from physical import *
import SQLiteParser
from System.Convert import IsDBNull
from struct import *
from array import array
import time, codecs, time, sys, re, os, datetime

'''
Script Name: spi_ufed_whatsapp_email_multiFormat_v2.py
Version: 2
Revised Date: 11/09/18
Python Version: 2.7.13
Description: A UFED PA Script to load Whatsapp's export to email (or similar) files on Physical Analyser chat section.
Copyright: 2018 Alberto Magno <alberto.magno@gmail.com> 
URL: https://github.com/kraftdenker/cellebrite-UFEDPA-scripts
--
- ChangeLog -
v1 - [24-10-17]: Wrote original code
v2 - [11-09-18]: Expanded date_patterns to variations based on device's configuration.
'''

#planejamento codigo do processador

# localizar arquivos no diretorio com filtragem por nome
# processar arquivo de contatos (contacts.txt) nome=jid.
# loop conversas
#	abrir cada arquivo de conversas ("Conversa do WhatsApp com [NOME_CHAT].txt")
#	abrir um chat no UFED baseado no nome do arquivo identificado.
#	loop linhas
#
#		processar as linhas (##/##/##, prefixo identificador de linha) 
#		linha ##/##/##, HH:MM - [CONTATO]:contains[arquivo anexado]?buscarArquivoAnexar
#			?buscar anexo 

class SPIWhatsAppEmailsParser(object):
   
	fsNodesOrdered = sorted(ds.FileSystems, key=lambda fs: str(fs)[str(fs).rfind('(')+1:str(fs).rfind('nodes)')-1], reverse=True)

	contacts = {}
	chats = {}
	sec_chats = {}
	
	date_patterns = {"datetime_format_1" : "(?P<datetime>\d{2}/\d{2}/\d{2}\s{1}\d{1,2}:\d{1,2})", "datetime_format_2" : "(?P<datetime>\d{2}/\d{2}/\d{2},\s{1}\d{1,2}:\d{1,2})", "datetime_format_3" : "(?P<datetime>\d{2}/\d{2}/\d{2},\s{1}\d{1,2}:\d{1,2}\s{1}(A|P)M)", "datetime_format_4" : "(?P<datetime>\d{2}/\d{2}/\d{4},\s{1}\d{1,2}:\d{1,2})"} 
	#date_format_1 dd/MM/yyyy HH24:mm #date_format_2 dd/MM/yyyy, HH24:mm #date_format_3 dd/MM/yyyy, HH:mm
	message_pattern = "\s{1}-\s{1}(?P<name>(.*?)):\s{1}(?P<message>(.*?))$"
	action_pattern = "\s{1}-\s{1}(?P<action>(.*?))$"

	action_strings = {
	"admin": "administrador",
	"change_icon": "icone do grupo alterado",
	"change_subject": "alterado o topico",
	"added": "adicionado",
	"left": "saiu",
	"removed": "removido"
	}
	class WhatsAppChatElement:
		def __init__(self, datetime, name, message, action):
			#self.datetime = datetime
			# finned datetime parser 
			# date_format_1 dd/MM/yyyy HH24:mm
			#print datetime
			#normalize date data
			# datetime_format_1 and 2 HH24
			matchDateTime = re.match(r'(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{2,4})[,]{0,1}\s{1}(?P<hour>\d{1,2}):(?P<minute>\d{1,2})',datetime)
			yearPlus = 0
			if not matchDateTime is None:
				if (len(matchDateTime.group('year'))==2):
					yearPlus = 2000
				dt = DateTime(int(matchDateTime.group('year'))+yearPlus,int(matchDateTime.group('month')),int(matchDateTime.group('day')),int(matchDateTime.group('hour')),int(matchDateTime.group('minute')),0)
				self.datetime = TimeStamp(dt)
			#datetime_format_3 HH12 AM - PM
			else:
				matchDateTime = re.match(r'(?P<day>\d{2})/(?P<month>\d{2})/(?P<year>\d{2}),\s{1}(?P<hour>\d{1,2}):(?P<minute>\d{1,2})\s[1](?P<ampm>((A|P)M))',datetime)
				if not matchDateTime is None:
					HH12 = 0
					if matchDateTime.group('ampm').contains('P'):
						HH12 = 12
					dt = DateTime(int(matchDateTime.group('year'))+2000,int(matchDateTime.group('month')),int(matchDateTime.group('day')),int(matchDateTime.group('hour'))+HH12,int(matchDateTime.group('minute')),0)
					self.datetime = TimeStamp(dt)
			
			self.name = name
			self.message = message
			self.action = action


	class WhatsAppChat:
		def __init__(self, filename):
			self.filename = filename

		def open_file(self):
			x = codecs.open(self.filename,'r',"utf-8-sig")
			y = x.read()
			content = y.splitlines()
			return content

	class WhatsApp_Email_Parser:
		def parse_message(self,str):
			for pattern in map(lambda x:x+SPIWhatsAppEmailsParser.message_pattern, SPIWhatsAppEmailsParser.date_patterns.values()):
				m = re.match(pattern, str)
				#if m:
				#	print 'MSG:',m.group('datetime')
				if m:
					return (m.group('datetime'), m.group('name'), m.group('message'), None)

			# if code comes here, message is continuation or action
			for pattern in map(lambda x:x+SPIWhatsAppEmailsParser.action_pattern, SPIWhatsAppEmailsParser.date_patterns.values()):
				m = re.match(pattern, str)
				if m:
					if any(action_string in m.group('action') for action_string in SPIWhatsAppEmailsParser.action_strings.values()):
						for pattern in map(lambda x: "(?P<name>(.*?))"+x+"(.*?)", SPIWhatsAppEmailsParser.action_strings.values()):
							m_action = re.match(pattern, m.group('action'))
							if m_action:
								return (m.group('datetime'), m_action.group('name'), None, m.group('action'))

						sys.stderr.write("[failed to capture name from action] - %s\n" %(m.group('action')))
						return (m.group('datetime'), None, None, m.group('action'))

			#prone to return invalid continuation if above filtering doesn't cover all patterns for messages and actions
			return (None, None, str, None)
		def process(self, content):
			messages = []
			null_chat = SPIWhatsAppEmailsParser.WhatsAppChatElement('', '', '', '')
			messages.append(null_chat)
			row_count = 0
			for row in content:
				parsed = self.parse_message(row)
				if parsed[0] is None:
					#print "row:",row_count, "appended"
					if not messages[-1].message is None:
						messages[-1].message += parsed[2]
					else:
						messages[-1].message = parsed[2]
				else:
					#print "parsed message"
					messages.append(SPIWhatsAppEmailsParser.WhatsAppChatElement(*parsed))			
				row_count = row_count + 1	
			#print 'Total:',row_count
			messages.remove(null_chat)
			return messages
			
	def __init__(self):
		self.APP_NAME = 'WhatsApp (EmailExport)'
		self.user_account=UserAccount()
		# TelegramID to contact
		self.contacts={}

	def clean_contacts(self):
		remove_list = []
		contact_list = ds.Models[Contact]
		for contact in contact_list:
			if str(contact.Source)=="WhatsApp (EmailExport)":
				remove_list.Add(contact)
		contact_list.RemoveRange(remove_list)

	def clean_messages(self):
		remove_list = []
		msg_list = ds.Models[InstantMessage]
		for msg in msg_list:
			if str(msg.SourceApplication.Value)=="WhatsApp (EmailExport)":
				remove_list.Add(msg)
		msg_list.RemoveRange(remove_list)		
			
	def clean_chats(self):
		remove_list = []
		chat_list = ds.Models[Chat]
		for chat in chat_list:
			if str(chat.Source.Value)=="WhatsApp (EmailExport)":
				remove_list.Add(chat)
		chat_list.RemoveRange(remove_list)		 
		
	def filter_non_printable(self,str):
		return ''.join([c for c in str if ord(c) > 31 or ord(c) == 9])	   

	def load_property_java_file(self,filepath, sep='=', comment_char='#'):
		"""
		Read the file passed as parameter as a properties file.
		"""
		props = {}
		with open(filepath, "rt") as f:
			for line in f:
				l = line.strip()
				if l and not l.startswith(comment_char):
					key_value = l.split(sep)
					key = key_value[0].strip()
					value = sep.join(key_value[1:]).strip().strip('"') 
					props[key] = value 
		return props
	
	def parse(self):
	
		results = []
		self.clean_messages()
		self.clean_chats()
		self.clean_contacts()
		self.decode_contacts()
		self.decode_messages()
				
		results+=self.contacts.values()
		
		return results
		
	
	def decode_contacts(self):
		#creating new UserID
		uid = UserID()

		#setting the Deleted State of the UserID
		uid.Deleted = DeletedState.Intact
		#Setting values
		uid.Category.Value = self.APP_NAME+ " Id"
		uid.Value.Value = "Proprietario do dispositivo"		   
		
		#creating new UserAccount
		ua = UserAccount()

		#setting the Deleted State and other Properties of the UserAccount 
		ua.Deleted = DeletedState.Intact
		ua.ServiceType.Value = self.APP_NAME
		ua.Entries.Add(uid)
		
		#self.contacts[ua_id] = ua 
		self.user_account = ua

		
		#going over the contacts files 
		contacts = self.load_property_java_file(pathContactFile)
		for k in contacts.keys():	  
			#creating new UserID field
			uid = UserID()
			uid.Deleted = DeletedState.Intact
			uid.Category.Value = self.APP_NAME+ " Id"
			uid.Value.Value = k
			contact = Contact()
			contact.Name.Value = k
			contact.Deleted = DeletedState.Intact
			contact.Source.Value = self.APP_NAME
			contact.Entries.Add(uid)
			ph = PhoneNumber()
			ph.Deleted = DeletedState.Intact
			ph.Value.Value = contacts[k].split("@")[0][2:]
			contact.Entries.Add(ph)
			ds.Models[Contact].Add(contact)
	
	def parse_whatsapp_message(self,lines):
		linst_of_messages = []
		set_of_sender = set()
		for l in lines:
			matchChat = re.match(r'(?P<date>\d{2}/\d{2}/\d{2})(?P<time>\s{1}\d{2}:\d{2})\s{1}-\s{1}(?P<name>(.*?)):\s{1}(?P<message>(.*?))$',line)
			if matchChat:
				print matchChat.group()
				print matchChat.group(1)
				print matchChat.group(2)
			else:
				print "no match!!"
	def findFile(self,fileName):
		print " ****** " + fileName
		for fs in self.fsNodesOrdered:
			foundFile = fs.GetFirstNode(fileName)
			if not foundFile is None:
				return foundFile
		return None
	def decode_messages(self):
		files = [f for f in os.listdir(currentDir) if re.match(r'Conversa do WhatsApp com (.*)\.txt', f)]
		repeated_chats = []
		for f in files:
			#todo: remove repeated extraction files.
			"""repeted_extraction_parse = re.match(r'Conversa do WhatsApp com (.*)\(\d\)\.txt', f)
			if not repeted_extraction_parse is None:
				print "Chat ",f,"repeated."
				repeated_chats.add(f)
			"""
			#print "Decoding messagens in "+f
			#chatFile=codecs.open(currentDir+"/"+f,"r", "utf-8-sig")
			
			ws_chat = self.WhatsAppChat(currentDir+"/"+f)	
			content = ws_chat.open_file()
			chat = Chat()
			chat.Deleted = DeletedState.Intact
			rchat_name_parser = re.match(r'Conversa do WhatsApp com (.*)\.txt', f)
			chat.Id.Value = rchat_name_parser.group(1)
			chat.Source.Value = "WhatsApp (EmailExport)"
			ws_parser = self.WhatsApp_Email_Parser()
			count =0 
			parties = set()
			parties.add(Party.MakeTo("Participantes do bate-papo \'"+rchat_name_parser.group(1)+"\'",None))
			ancient_date = time.localtime() #today
			recent_date = TimeStamp.FromUnixTime(0) # pre nintendo era
			for m in ws_parser.process(content):
				im = InstantMessage()
				im.Deleted = DeletedState.Intact
				if m.action is None:
					im.Body.Value = m.message
					anexo_parser = re.match(r'(.*)\s\(arquivo anexado\)', m.message)
					if not anexo_parser is None: #has attachement
							att = Attachment()
							att.Filename.Value = anexo_parser.group(1)
							att.Deleted = DeletedState.Intact
							
							r = self.findFile(anexo_parser.group(1))
							if not r is None:
								att.Data.Source = r.Data
								im.Attachments.Add(att)
							else:
								print "!!!WARNING!!! Attachment file not found:",anexo_parser.group(1)
					anexo_ausente = re.match(r'<M\w{1}dia omitida>', m.message)
					if not anexo_ausente is None: 
						im.Body.Value = im.Body.Value+"-<O anexo nao foi localizado no dispositivo>"
								
				else:
					im.Body.Value = "("+m.action+")"
				party = Party.MakeFrom(m.name,None)
				parties.add(party)
				im.From.Value = party
				im.TimeStamp.Value = m.datetime
				if im.TimeStamp.Value < ancient_date:
					ancient_date = im.TimeStamp.Value
				if im.TimeStamp.Value > recent_date:
					recent_date = im.TimeStamp.Value 
				
				chat.Messages.Add(im)
				chat.StartTime.Value = ancient_date
				chat.LastActivity.Value = recent_date
				count = count +1
			
			for p in parties:
				chat.Participants.Add(p) 

			ds.Models[Chat].Add(chat)
			
		
		print "finished"
print "Starting spi_ufed_whatsapp_email script. (SPI POWERED)"
print "Processing..."
startTime = time.time()
currentDir= __file__[:__file__.rfind('\\')]+"\\EmailWhatsApp\\"
#debugFile = currentDir+"/log.txt"
pathContactFile = currentDir+'/contacts.txt'

#calling the parser for results
results = SPIWhatsAppEmailsParser().parse()

print "Finished",('The script took {0} seconds !'.format(time.time() - startTime))
