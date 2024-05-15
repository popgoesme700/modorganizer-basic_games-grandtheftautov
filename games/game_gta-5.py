import os
import shutil

import mobase
from collections.abc import Mapping
from dataclasses import dataclass
from ..basic_features import BasicModDataChecker,GlobPatterns
from ..basic_game import BasicGame
from PyQt6 import QtCore,QtWidgets

from typing import Any
from .gta_5 import RPF,GTA5Keys

class GTAVModDataChecker(BasicModDataChecker):
	def __init__(self):
		super().__init__(GlobPatterns(
			move={
				"*.dll":"root/",
				"*.exe":"root/",
			},
			delete=[
				"*.txt",
				"*.url",
				"*.docx",
				"*.png",
				"*.log",
			],
			valid=[
				"*.asi",
				"*.log",
				"*.ini",
				"*.xml",
				"root",
				"mods",
				"openiv",
				"scripts",
			],
		))
	
	_extra_move_items={
		"bin/ScriptHookV.dll":"root/",
		"bin/dinput8.dll":"root/",
		"bin/NativeTrainer.asi":"",
	}

	_dont_move_these_rpf={

	}

	def _move_dlcpack_rpf(self,filetree:mobase.IFileTree)->mobase.IFileTree:
		QtCore.qInfo(str(filetree))
		return filetree

	
	def dataLooksValid(self,filetree:mobase.IFileTree)->mobase.ModDataChecker.CheckReturn:
		parent=filetree.parent()
		if parent is not None and self.dataLooksValid(parent) is self.FIXABLE:
			return self.FIXABLE
		
		status=super().dataLooksValid(filetree)
		if any(filetree.exists(mf) for mf in self._extra_move_items):
			status=self.FIXABLE

		return status

	def _clear_empty_folder(self,filetree:mobase.IFileTree|None):
		if filetree is None: return
		while not filetree:
			parent=filetree.parent()
			filetree.detach()
			if parent is None: break
			filetree=parent
	
	def fix(self,filetree:mobase.IFileTree)->mobase.IFileTree:
		filetree=super().fix(filetree)
		filetree=self._move_dlcpack_rpf(filetree)
		for src,tgt in self._extra_move_items.items():
			if file:=filetree.find(src):
				parent=file.parent()
				filetree.move(file,tgt)
				self._clear_empty_folder(parent)
			
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
		organizer.onAboutToRun(self.onAboutToRun)

		return True
	
	@staticmethod
	def outputAbout(rpf:RPF.RPF):
		QtWidgets.QMessageBox.about(None,"Version","0x"+str(rpf.header.version.value.to_bytes(4).hex().upper()))
		QtWidgets.QMessageBox.about(None,"TOC Size",str(rpf.header.toc_size))
		QtWidgets.QMessageBox.about(None,"Entries",str(rpf.header.entry_size))
		QtWidgets.QMessageBox.about(None,"Unknown","0x"+str(rpf.header.unknown.to_bytes(4).hex().upper()))
		QtWidgets.QMessageBox.about(None,"Encrypted","0x"+str(rpf.header.encrypted.value.to_bytes(4).hex().upper()))
	
	@staticmethod
	def writeOutput(rpf:RPF.RPF,to_path:str):
		res=rpf.write(to_path)
		QtWidgets.QMessageBox.about(None,"The Bytes Written","0x"+str(res[0].hex().upper()))
		QtWidgets.QMessageBox.about(None,"Bytes Written",""+str(res[1]))

	def onAboutToRun(self,exe:str,work_dir:QtCore.QDir,args:str)->bool:
		rpf=RPF.RPF(self.gameDirectory().absoluteFilePath("update/update.rpf"))
		self.outputAbout(rpf)

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
		def on_update(msg:str):
			QtWidgets.QMessageBox.about(None,"Key Generation Status",msg)
		GTA5Keys.GTA5Keys.generate(self.gameDirectory().absoluteFilePath("GTA5.exe"),on_update)

		write=open(self._organizer.pluginDataPath()+"/keys.bin","wb")
		write.write(GTA5Keys.GTA5Keys.pc_aes_key)
		write.write(0x0000.to_bytes(2))
		for key in GTA5Keys.GTA5Keys.pc_ng_keys:
			write.write(key)
			write.write(0xFF.to_bytes())
		write.write(0x0000.to_bytes(2))
		for list in GTA5Keys.GTA5Keys.pc_ng_decrypttables:
			for list in list:
				for key in list:
					write.write(key.to_bytes(4))
					write.write(0xFF.to_bytes())
		write.write(0x0000.to_bytes(2))
		write.write(GTA5Keys.GTA5Keys.pc_lut)
		write.write(0x0000.to_bytes(2))
		#modspath=self.gameDirectory().absoluteFilePath("mods")
		#if not os.path.exists(modspath): os.mkdir(modspath)
		super().initializeProfile(directory, settings)
		