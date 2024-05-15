import sys
import os
import io

import typing
from typing import TypeAlias
from enum import Enum

from Crypto.Cipher import AES

from PyQt6 import QtCore

StrOrBytesPath:TypeAlias=str|bytes|os.PathLike[str]|os.PathLike[bytes]
FileDescriptorOrPath:TypeAlias=int|StrOrBytesPath

#Define RPF Versions
class RPFVersion(Enum):
	UNKNOWN=0x00000000
	GTAIV=0x52504632
	MIDNIGHTCLUB=0x52504633
	MAXPAYNE=0x52504634
	RDR=0x52504636
	GTAV=0x52504637
	RDR2=0x52504638

	@classmethod
	def _missing_(cls,value:object):
		return RPFVersion.UNKNOWN

#Define RPF Encryption
class RPFEncryption(Enum):
	NONE=0x00000000
	OPENIV=0x4E45504F
	AES=0x0FFFFFF9
	NG=0x0FEFFFFF

	@classmethod
	def _missing_(cls,value:object):
		return RPFEncryption.NG

class RPFHeader:
	version=RPFVersion.GTAV
	toc_size=2048
	entry_size=0
	unknown=0
	encrypted=RPFEncryption.OPENIV

	def __init__(self,file:typing.BinaryIO|None=None):
		super().__init__()
		if file is None: return
		endian=sys.byteorder
		QtCore.qInfo(endian)
		self.version=RPFVersion(int.from_bytes(file.read(4),endian))
		self.toc_size=int.from_bytes(file.read(4),endian)
		self.entry_size=int.from_bytes(file.read(4),endian)
		if self.version.value<RPFVersion.GTAV.value and self.version.value>=RPFVersion.GTAIV.value:
			self.unknown=int.from_bytes(file.read(4),endian)
		if self.version.value>=RPFVersion.GTAIV.value:
			self.encrypted=RPFEncryption(int.from_bytes(file.read(4),endian))
	
	def write(self,file:typing.BinaryIO|None=None)->tuple[bytes,int]:
		endian=sys.byteorder
		bio=io.BytesIO()
		bw=bio.write(self.version.value.to_bytes(4,endian))
		bw+=bio.write(self.toc_size.to_bytes(4,endian))
		bw+=bio.write(self.entry_size.to_bytes(4,endian))
		if self.version.value<RPFVersion.GTAV.value and self.version.value>=RPFVersion.GTAIV.value: bw+=bio.write(self.unknown.to_bytes(4,endian))
		if self.version.value>=RPFVersion.GTAV.value: bw+=bio.write(self.encrypted.value.to_bytes(4,endian))
		rtn=(bio.getvalue(),bw)
		if file is not None:
			bw=file.write(rtn[0])
			rtn=(rtn[0][:bw],bw)
		return rtn

class RPFDir:
	pass

class RPF:
	header=RPFHeader()
	root=RPFDir()
	_ofile=None

	def __init__(self,file:FileDescriptorOrPath|typing.BinaryIO|None=None):
		super().__init__()
		if isinstance(file,typing.BinaryIO): self._ofile=file
		elif file is not None: self._ofile=open(file,"r+b")
		if self._ofile:
			self.header=RPFHeader(self._ofile)
	
	def __enter__(self):
		return self

	def __exit__(self,exc_type,exc_value,traceback): # type: ignore
		if self._ofile is not None: self._ofile.close()
	
	def __del__(self):
		if self._ofile is not None: self._ofile.close()

	def write(self,file:FileDescriptorOrPath|typing.BinaryIO|None=None)->tuple[bytes,int]:
		if self._ofile is not None: self._ofile.seek(0)
		if file is not None:
			if self._ofile is not None: self._ofile.close()
			if isinstance(file,typing.BinaryIO): self._ofile=file
			elif file: self._ofile=open(file,"r+b")
		bw=0
		byt=bytearray()
		res=self.header.write(self._ofile)
		byt.extend(res[0])
		bw+=res[1]
		if self._ofile is not None: self._ofile.truncate()
		return (bytes(byt),bw)