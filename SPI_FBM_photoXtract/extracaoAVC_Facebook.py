#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
Copyright (C) 2019  Alberto Magno
Created on 31 Jan 2019
@author: Alberto Magno - alberto.magno@gmail.com
GNU GENERAL PUBLIC LICENSE -Copyright: 2019 Alberto Magno <alberto.magno@gmail.com>
Objective:
Pass trought all chats taking screenshots of all messages dragging the messages list.
'''


import re
import sys
import os
import string
import logging
import time
import werkzeug
import datetime
import StringIO


try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.:]+')

package = 'com.facebook.orca'
activity = '.auth.StartScreenActivity'
extraction_path = werkzeug.utils.secure_filename('./FBMphotoXtract_'+datetime.datetime.now().isoformat())

component = package + "/" + activity
TOUCH_SLEEP = 2;
TOUCH_LONG_SLEEP = 4;

visitedChats = [];
logging.basicConfig(level=logging.DEBUG);

def norm_unicode_filename(text, delim=u'-'):
    #Generates an slightly worse ASCII-only slug.
    result = []
    for word in _punct_re.split(text):
        if word:
            result.append(word)
    return unicode(delim.join(result))

def putMainScreen(vc):
	isFBMHome = False
	while not isFBMHome:
		searchBox = vc.findViewsWithAttribute('class','android.widget.TextView')
		for item in searchBox:
			#print item.getText(), item.getContentDescription(), item.getTag()
			if item.getText()=='Pesquisar':
				isFBMHome = True
				print 'HOME SWEET HOME'
				vc.dump()
				break
		if not isFBMHome:
			vc.device.press('KEYCODE_BACK')
			vc.dump()

def toStart(vc):
	isFBMHomeTop = False
	vc.dump()
	while not isFBMHomeTop:
		
		searchBox = vc.findViewsWithAttribute('class','android.view.ViewGroup')
		for item in searchBox[0].children:
			print item.getText(), item.getContentDescription(), item.getTag()
			
			if item.getText()=='Online':
				isFBMHomeTop = True
		if not isFBMHomeTop:
			print "swipe up"
			device, serialno = ViewClient.connectToDeviceOrExit();
			vc = ViewClient(device, serialno)
			device.dragDip((169.0, 197.0),(173.0, 557.0), 1000, 20,0)
		vc.dump()
def loadScreenshots():
	# Read all chats in list
	device, serialno = ViewClient.connectToDeviceOrExit();
	device.press('KEYCODE_HOME');
	device.startActivity(component=component);
	ViewClient.sleep(TOUCH_LONG_SLEEP);
	vc = ViewClient(device, serialno, autodump=True)
	putMainScreen(vc)
	toStart(vc) ##coments if necessary continue a extraction
	vc.dump()
	new_chats = True
	while new_chats: #check screen changes (in chat list) after dragging
		
		# track the chat list beginning.
		brute_chatList = vc.findViewsWithAttribute('class','android.view.ViewGroup')
		
		if brute_chatList[0] is None:
			logging.error('Cant go back to Facebook Home')
			quit();
		
		# capture new chats in screen list
		chatList = []
		new_chats = False
		
		for c in brute_chatList[0].children:
			if len(c.getText())>0 and c.getText()!='Online' and not c.getContentDescription() in visitedChats:
				print c.getContentDescription().encode('utf-8')
				chatList.append(c)
				new_chats = True
		print "new Chats:(",len(chatList),")", 'total ',len(visitedChats)
		# process new chats
		for chat in chatList:
			print '->'+chat.getContentDescription().encode('utf-8'), chat.getTag(), chat.getUniqueId()
			path = ''
			if isinstance(chat.getContentDescription(), unicode):
				path = unicode(extraction_path+'/'+norm_unicode_filename(chat.getContentDescription()))
			if isinstance(chat.getContentDescription(), str):
				path = extraction_path+'/'+werkzeug.utils.secure_filename(chat.getContentDescription().encode('utf-8'))
			
			os.mkdir(path, 0777)
						
			device, serialno = ViewClient.connectToDeviceOrExit();
			vc = ViewClient(device, serialno)
			
			chat.touch()
			#print 'touching...'
			if vc.isKeyboardShown():
				device.press('KEYCODE_BACK')
			root = vc.findViewsWithAttribute('class','android.view.ViewGroup');
			#print "Grupo:", len(root), root[0].getContentDescription(), root[0].getText()
			vc = ViewClient(device, serialno)
			
			# snapshot screen
			screenshot_count = 1 
			before_dump = ''
			strScreen = StringIO.StringIO()
			vc.traverse(transform=ViewClient.TRAVERSE_CITPS, stream=strScreen)
			after_dump = strScreen.getvalue()
			while before_dump != after_dump: #check screen changes (in msgs list) after dragging
				before_dump = after_dump
				print 'screenshot',screenshot_count
				device.takeSnapshot().save(path+'/screenshot_'+str(screenshot_count)+".png", 'PNG')
				device, serialno = ViewClient.connectToDeviceOrExit();
				vc = ViewClient(device, serialno)
				#print 'connected?',device.checkConnected()
				device.dragDip((169.0, 297.0),(173.0, 600.0), 1000, 20,0)
					
				attemptCount = 0
				while attemptCount < 5:
					try:
						attemptCount = attemptCount + 1
						vc = ViewClient(device, serialno)
						break
					except:
						print 'Houston...we have a problem (BEEP) - small drag tilt'
						device.dragDip((169.0, 297.0),(173.0, 310.0), 1000, 20,0)
				if attemptCount == 5:
					print 'ERROR'
					exit(1)
				strScreen = StringIO.StringIO()
				vc.traverse(transform=ViewClient.TRAVERSE_CITPS, stream=strScreen)
				after_dump = strScreen.getvalue()
				screenshot_count = screenshot_count + 1
			visitedChats.append(chat.getContentDescription())
			putMainScreen(vc)
			#device.press('KEYCODE_BACK');	
		# drag chat list
		device.dragDip((173.0, 560.0),(169.0, 150.0), 1000, 20,0)
		vc = ViewClient(device, serialno)
		#Am i in FBM home?
		print 'put main screen'
		putMainScreen(vc)
		
	print 'Total chats:',len(visitedChats)



os.mkdir(extraction_path)
loadScreenshots();

print 'Total:',len(visitedChats)






