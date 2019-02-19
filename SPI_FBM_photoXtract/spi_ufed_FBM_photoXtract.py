from physical import *
from System.Convert import IsDBNull
from struct import *
from array import array
import time, codecs, time, sys, re, os, datetime

'''
Copyright (C) 2019  Alberto Magno
Created on 31 Jan 2019
@author: Alberto Magno - alberto.magno@gmail.com
GNU GENERAL PUBLIC LICENSE -Copyright: 2019 Alberto Magno <alberto.magno@gmail.com>
Objective:
Load screenshot of messages chats.
'''

#planejamento codigo do processador de carga

# localizar diretorios com fotos, listar os diretorios

# loop nos diretorios com fotos
#	abrir cada diretorio, criar chat com nome do diretorio.
#   criar mensagem unica com todas as fotos anexas.

class SPIFBMPhotoXtract(object):
   
	fsNodesOrdered = sorted(ds.FileSystems, key=lambda fs: str(fs)[str(fs).rfind('(')+1:str(fs).rfind('nodes)')-1], reverse=True)
	
	
	def clean_messages(self):
		remove_list = []
		msg_list = ds.Models[InstantMessage]
		for msg in msg_list:
			if str(msg.SourceApplication.Value)==self.APP_NAME:
				remove_list.Add(msg)
		msg_list.RemoveRange(remove_list)		
			
	def clean_chats(self):
		remove_list = []
		chat_list = ds.Models[Chat]
		for chat in chat_list:
			if str(chat.Source.Value)==self.APP_NAME:
				remove_list.Add(chat)
		chat_list.RemoveRange(remove_list)		
	
	def getint(self, file):
		_, num = file.Name.split('_')
		num, _ = num.split('.')
		return int(num)
	
	def getModifyTime(self, file):
		return file.Children[0].ModifyTime.Value.Ticks
		
	def read_directories(self):
		for fs in self.fsNodesOrdered:
			if fs.Name.startswith('FBMphotoXtract'): #read all photo extraction made 
				orderedMDTime = sorted (fs.Directories,key=self.getModifyTime, reverse=True)
				for photoDir in orderedMDTime: #for each dir create a chat container
					chat = Chat()
					chat.Deleted = DeletedState.Intact
					chat.Id.Value = "Fotografias da conversa com "+photoDir.Name 
					chat.Source.Value = self.APP_NAME
					party = Party.MakeFrom(photoDir.Name,None)
					chat.Participants.Add(party)
					chat.Description.Value = 'Registro fotografico (screenshot) da conversa com '+photoDir.Name
					#real all photo files
					orderedDirFiles = sorted(photoDir.Files, key=self.getint)
					for photoFile in orderedDirFiles:
						im = InstantMessage()
						im.Deleted = DeletedState.Intact
						im.SourceApplication.Value==self.APP_NAME
						im.Body.Value = 'Duplo clique na imagem abaixo para visualizar.'
						im.From.Value = party
						att = Attachment()
						att.Filename.Value = photoFile.Name
						att.Data.Source = photoFile.Data
						im.Attachments.Add(att)
						chat.Messages.Add(im)
					chat.Messages.Sort()
					ds.Models[Chat].Add(chat)
					
				
	def load(self):
		self.clean_messages()
		self.clean_chats()
		self.read_directories()
				
	def __init__(self):
		self.APP_NAME = 'Facebook (photoXtract)'
 
print "Starting spi_ufed_FBMphotoXtract script. (SPI POWERED)"
print "Processing..."
startTime = time.time()

#calling the parser for results
SPIFBMPhotoXtract().load()

print "Finished",('The script took {0} seconds !'.format(time.time() - startTime))
