import os

import mobase
from collections.abc import Mapping
from dataclasses import dataclass
from ..basic_features import BasicModDataChecker,GlobPatterns
from ..basic_game import BasicGame
from PyQt6 import QtCore

from typing import Any

class GTAVModDataChecker(BasicModDataChecker):
	def __init__(self):
		super().__init__(GlobPatterns(
			move={
				"**.dll":"root/",
				"*.asi":"",
			},
			delete=[
				"*.txt",
				"*.url",
				"*.docx"
			],
			valid=[
				"*.rpf"
				"root",
			],
		))
	
	_files_to_move={
		"*.rpf":"mods",
	}
	
	def dataLooksValid(self,filetree:mobase.IFileTree)->mobase.ModDataChecker.CheckReturn:
		if super().dataLooksValid(filetree)==self.VALID: return self.VALID
		parent=filetree.parent()
		if parent is not None and self.dataLooksValid(parent) is self.FIXABLE:
			return self.FIXABLE
		status=self.INVALID
		if any(filetree.exists(f) for f in self._files_to_move):
			return self.FIXABLE
		regex=self._regex_patterns
		for e in filetree:
			name=e.name().casefold()
			if regex.move_match(name) is not None: return self.FIXABLE
			elif regex.valid.match(name):
				if status is self.INVALID: status=self.VALID

		return status
	
	def fix(self,filetree:mobase.IFileTree)->mobase.IFileTree:
		filetree=super().fix(filetree)
		QtCore.qInfo(str(filetree))
		return filetree

@dataclass
class PluginDefaultSettings:
	organizer:mobase.IOrganizer
	plugin_name:str
	settings:Mapping[str,mobase.MoVariant]

	def is_plugin_enabled(self)->bool:
		return self.organizer.isPluginEnabled(self.plugin_name)
	
	def apply(self)->bool:
		if not self.is_plugin_enabled(): return False
		for setting,value in self.settings.items():
			self.organizer.setPluginSetting(self.plugin_name,setting,value)
		return True

class GTAVGame(BasicGame):
	Name="Grand Theft Auto V Support Plugin"
	Author="popgoesme700"
	Version="0.1"

	GameName="Grand Theft Auto V"
	GameShortName="gtav"
	GameSteamId=271590
	GameEpicId="9d2d0eb64d5c44529cece33fe2a46482"

	GameBinary="PlayGTAV.exe"
	GameDataPath="%GAME_PATH%"
	GameDocumentsDirectory=(
		"%USERPROFILE%/Documents/Rockstar Games/"
		"GTA V"
	)
	GameSavesDirectory="%GAME_DOCUMENTS%/Profiles"

	def init(self,organizer:mobase.IOrganizer)->bool:
		super().init(organizer)
		self._featureMap[mobase.ModDataChecker]=GTAVModDataChecker()

		self._rootbuilder_settings=PluginDefaultSettings(
			organizer,
			"RootBuilder",
			{
				"uvfsmode":False,
				"linkmode":False,
				"linkonlymode":True,
				"backup":True,
				"cache":True,
				"autobuild":True,
				"redirect":False,
				"installer":False,
				"exclusions":"*.rpf,x64,update,Redistributables",
				"linkextensions":"dll,exe",
			},
		)

		def apply_rootbuilder_settings_once(*args:Any):
			if not self.isActive() or not self._get_setting("configure_RootBuilder"): return
			if self._rootbuilder_settings.apply():
				QtCore.qInfo(f"RootBuilder configured for {self.gameName()}")
				self._set_setting("configure_RootBuilder",False)
		organizer.onUserInterfaceInitialized(apply_rootbuilder_settings_once)
		organizer.onPluginEnabled("RootBuilder",apply_rootbuilder_settings_once)
		organizer.onPluginSettingChanged(self._on_setting_update)

		return True

	def settings(self)->list[mobase.PluginSetting]:
		sets=super().settings()
		sets.append(mobase.PluginSetting(
			"configure_RootBuilder",
			"Configures RootBuilder for Grand Theft Auto V if installed and enabled",
			True,
		))
		return sets
	
	def _on_setting_update(self,plugin_name:str,setting:str,old:mobase.MoVariant,new:mobase.MoVariant):
		if plugin_name!=self.name(): return
		match setting:
			case _: pass

	def _get_setting(self,setting:str)->mobase.MoVariant:
		return self._organizer.pluginSetting(self.name(),setting)

	def _set_setting(self,setting:str,value:mobase.MoVariant):
		self._organizer.setPluginSetting(self.name(),setting,value)
	
	def executables(self)->list[mobase.ExecutableInfo]:
		return [
			mobase.ExecutableInfo(
				self.gameName(),
				QtCore.QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
			).withArgument("-scOfflineOnly"),
			mobase.ExecutableInfo(
				"OpenIV",
				QtCore.QFileInfo(QtCore.QDir(QtCore.QStandardPaths.standardLocations(QtCore.QStandardPaths.StandardLocation.GenericDataLocation)[0]).absoluteFilePath("New Technology Studio/Apps/OpenIV/OpenIV.exe")),
			).withWorkingDirectory(self.gameDirectory().absolutePath()),
		]
	
	def iniFiles(self)->list[str]:
		ini=super().iniFiles()
		ini.append("settings.xml")
		return ini
	
	def initializeProfile(self,directory:QtCore.QDir,settings:mobase.ProfileSetting):
		modspath=self.gameDirectory().absoluteFilePath("mods")
		if not os.path.exists(modspath): os.mkdir(modspath)
		super().initializeProfile(directory, settings)
		