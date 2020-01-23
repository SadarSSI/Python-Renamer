#!/usr/bin/env python
# encoding: UTF-8

import sys, os, re, subprocess, pathlib, argparse, yaml, time
import unicodedata as ud

from pprint import pprint
from yaml import load, FullLoader
from datetime import datetime, date, time, timedelta
from pathlib import Path

from qbittorrent import Client

# Command line parsing
ArgParser = argparse.ArgumentParser (prog='rname', description='Python renamer for qbitorrent and batch ', 
                                        usage='%(prog)s [options]',
                                        epilog="This script can be used with or without qbt. If the hash parameter is specified, the torrent will be removed from qbt. Otherwise, only a rename will be executed. ")
ArgParser.add_argument ('name', help='Name of existing File or Folder to rename')
ArgParser.add_argument ('--hash', nargs='?', help='[hash] If the hash parameter is specified, the torrent will be removed from Qbitorrent')
ArgParser.add_argument ('-mv', '--mv-single', action='store_true', default=False, help='Sometimes we want to move the file to the parent directory if it is alone in the folder.')
ArgParser.add_argument ('-yml', '--ymlFile', nargs='?', help="[Path/File Name] Yaml file which contains the connection information to the Qbt server and the words to delete / replace. By default the rname.yml file will be taken from the folder where this script is located")
ArgParser.add_argument ('--dry-run', action='store_true',	default=False, help='dry-run mode')

Args    = ArgParser.parse_args ()
Options = {
  'name'    : Args.name,
  'hash'    : Args.hash,
  'rmovsgl' : Args.mv_single,
  'ymlFile' : Args.ymlFile,
  'dry-run' : Args.dry_run
  }

#-----------------------------------------------------------------------------------------------------------------------------------------------------
class Logger(object):

  # constructeur
  def __init__(self, LogFilePath, NoStdOut=True, Verbose=False):
    self.LogFilePath = LogFilePath
    self.NoStdOut    = NoStdOut
    self.Verbose     = Verbose

    self.LOGGER_SEVERITY = {
      'INFO'    : 'INFO',
      'CRITICAL': 'CRITICAL',
      'ERROR'   : 'ERROR',
      'WARNING' : 'WARNING',
      'NOTICE'  : 'NOTICE',
      'DEBUG'   : 'DEBUG'
      }

    if self.LogFilePath is not None:
      try:
        self.LogFile
        raise Exception ("Logger : Log file [{}] already openned.".format (self.LogFilePath))
      except:
        self.LogFile = open (self.LogFilePath, 'a')

  def Close (self):
    """Close the log file
        RETURN:		True:	Log file is closed.
        False:	An error has occured. 
        """
    
    if self.LogFile is not None:
      self.LogFile.close ()
      self.LogFile	= None

    else:
      raise Exception ("Logger.Close(): Log file [{}] not open.".format ( self.LogFilePath ))

    return True
   
  def Log (self, Severity, Message):
    """ Logging function. Log in a log file if openned.
        Log to stdout/stderr if _NoStdOut is False.
        
          IN:		Severity	Muse be one of the severities described in the dictionnary LOGGER_SEVERITY.
                Message		The message to log.
          """     
    
    DateTime	= "{0:%Y-%m-%d %H:%M:%S}".format(datetime.now())
    LogLine		= "{} [{}]> {}\n".format (DateTime, self.LOGGER_SEVERITY[Severity], Message)

    try:
      if self.LogFile  is not None:
        self.LogFile.write (LogLine)

      if not self.NoStdOut :
        if Severity in {'CRITICAL', 'ERROR', 'WARNING', 'DEBUG'}:
          sys.stderr.write (LogLine)
        elif Severity == 'NOTICE':
          sys.stdout.write (LogLine)
        elif self.Verbose:
          sys.stdout.write (LogLine)

    except KeyError as e:
      sys.stderr.write ("Logger.Log(): Invalid Severity [{}]. (LogLine=[{}])".format (str (Severity), LogLine))

  "Various wrapper functions to Log() function. One per severity "
  def LogInfo (self, Message):
    self.Log ('INFO', Message)

  def LogCritical (self, Message):
    self.Log ('CRITICAL', Message)

  def LogError (self, Message):
    self.Log ('ERROR', Message)

  def LogWarning (self, Message):
    self.Log ('WARNING', Message)

  def LogNotice (self, Message):
    self.Log ('NOTICE', Message)

  def LogDebug (self, Message):
    self.Log ('DEBUG', Message)
#-----------------------------------------------------------------------------------------------------------------------------------------------------

def recursive_glob(rootdir='.', suffix=[]):
    return [os.path.join(looproot, filename)
            for looproot, _, filenames in os.walk(rootdir)
            for filename in filenames if filename in suffix ]

def deletefiles(Files):
  for file in Files:
    SLog.LogInfo ("delete file : [{}]".format( os.path.basename( file )) )
    if not Options['dry-run']:
      os.remove( file )

def ireplace(old, new, text):
    idx = 0
    while idx < len(text):
        index_l = text.lower().find(old.lower(), idx)
        if index_l == -1:
            return text
        text = text[:index_l] + new + text[index_l + len(old):]
        idx = index_l + len(new) 
    return text

def rname(oldname="", newname=""): 
  if oldname and newname:

    if os.path.isdir( oldname ) :
      SLog.LogInfo ("rname folder: [{}]".format( os.path.basename( oldname )) )
    else:
      SLog.LogInfo ("rename file : [{}]".format( os.path.basename( oldname )) )
      
    SLog.LogInfo ("to =======> : [{}]".format( os.path.basename( newname )) )

    if not Options['dry-run']:
      os.rename(oldname, newname)

def mvfile(srcPath=""): 
  if srcPath:

    #Parent path
    parentPath = os.path.dirname ( srcPath )
    fileNme = [ f for dirpath, dirnames, filenames in os.walk( torrentPath ) for f in filenames ][0]

    srcPathFile  = "{}/{}".format( srcPath, fileNme )
    destPathFile = "{}/{}".format( parentPath, fileNme )

    SLog.LogInfo ("move file   : [{}]".format( srcPathFile  ) )
    SLog.LogInfo ("to =======> : [{}]".format( destPathFile ) )

    if not Options['dry-run']:
      os.rename(srcPathFile, destPathFile)

def fchange(flist):
  # SLog.LogInfo ("flist {}".format(flist))
  
  for index, item in enumerate(flist):

    newname = ud.normalize('NFC', item[1])
    # SLog.LogInfo ("newname org => : [{}]".format( newname ) )
  
    for word in [ word for word in rlist['RmoveStrings'] if word.lower() in newname.lower() ]:
      newname = ireplace(word, '', newname)
      SLog.LogInfo ("RvmoveStr   : [{}]".format( newname ) )

    for word in [ word for word in rlist['RmoveSigns'] if word in newname ]:
      newname = ireplace(word, '', newname)
      SLog.LogInfo ("RvmoveSigns : [{}]".format( newname ) )
  
    # for word in rlist['ChangeStrings']: 
    for word in [word.split(',') for word in rlist['ChangeStrings'] if word.split(',')[0] in newname ]: 
      sword = word.split(",") # split to list
      SLog.LogInfo ("{} - {} - {} - {}".format(newname, word, sword[0], sword[1]))  
      newname = ireplace(sword[0], sword[1], newname)
      SLog.LogInfo ("ChgStrings  : [{}]".format( newname ) )
  
    # rplace space by .
    newname = ".".join(newname.split())

    # rplace too many .... by only .
    newname = '.'.join([j for j in (newname.split('.')) if j != ''])
    # SLog.LogInfo ("rplace .... by . [{}]".format( newname ) )
  
    # SLog.LogInfo ("rname newname={} vs item[1]={}".format(newname, item[1]))
    if newname != None and newname != str(item[1]):
      # nb : rmove '.' if first char
      # newname = newname[1:] if '.' == newname[0] else newname 
      rname( "/".join( [item[0], item[1]] ), "/".join([ item[0], newname[1:] if '.' == newname[0] else newname ]) )

      if os.path.isdir( "/".join([ item[0], newname ]) ):
        flist.clear()
        fchange ( [ (dirpath, d) for dirpath, dirnames, filenames in os.walk( torrentPath ) for d in dirnames ] )

def cmdProcess(cmd):
  try:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if len(result.stderr) > 1:
      SLog.LogInfo ("len={} , result.stderr={}".format(len(result.stderr), result.stderr))
      ExceptionMessage = result.stderr
    else:
      return result.stdout.replace("\n\n","\n")

  except Exception as e:
    ExceptionMessage = "({}) !!! Arrêt sur erreur !!! ligne ({}) [{}] {}\n".format (
                      sys._getframe().f_code.co_name, 
                      sys.exc_info()[2].tb_lineno, 
                      type (e).__name__, 
                      str (e) )

    SLog.LogCritical (ExceptionMessage)

  if ExceptionMessage is not None:
    raise Exception (ExceptionMessage)

# -- main ---------------------------------------------------------------------
if __name__ == '__main__' :
  
  try:

    LOG_FILE = "/var/log/rname.log"

    # Open log file
    SLog = Logger (LOG_FILE, False, True)
    SLog.LogInfo ("\n"+ "-" * 100)

    if Options['ymlFile']:
      YmlFile = Options['ymlFile']
    else:
      CurrentPath = (os.path.dirname(os.path.realpath( sys.argv[0] )))
      # YmlFile =  "/mnt/vol3To01/movies/in.coming/00.pgm/rname/rnam.yml"
      YmlFile =  "{}/rname.yml".format( CurrentPath )

      # Open & load Yaml File...
      SLog.LogInfo ("Open YmlFile '{}' ".format ( YmlFile ))
      rlist = yaml.load(open( YmlFile, 'r', encoding="utf-8"), FullLoader)

    # if hash is present
    if Options['hash']:

      # Cnx to qbitorrent server
      qb = Client(rlist['Qbitsrv']['address'])
      qb.login(rlist['Qbitsrv']['user'], rlist['Qbitsrv']['pwd'])

      hashFile   = Options['hash']
      SLog.LogInfo ("hash           : [{}]".format( hashFile ) )

      # Test if hash is correct
      if qb.torrents(hashes=hashFile) :

        for torrent in qb.torrents(hashes=hashFile):
          # Get torrent infos by the hash on qbitorrent server
          if torrent['hash'] == hashFile :
            savePath   = torrent['save_path']  
            nameFile   = torrent['name']
            magnet_uri = torrent['magnet_uri']

            SLog.LogInfo ("magnet_uri     : [{}]".format( magnet_uri ) )
            SLog.LogInfo ("torrent name   : [{}]".format( nameFile   ) )   
            SLog.LogInfo ("save path      : [{}]".format( savePath   ) ) 
            
            if not Options['dry-run']:
              # delete torrent file du serveur qbitorrent
              SLog.LogInfo ("-" * 10 )   
              SLog.LogInfo ("del qbitorrent : [{}]".format( nameFile ) )
              SLog.LogInfo ("-" * 10 )   
              qb.delete(hashFile)
      else:
        SLog.LogCritical ("Bad hash   : [{}]".format( hashFile ))
        SLog.LogCritical ("-_|_-                                         -_|_-")
        SLog.LogCritical ("      -_|_-                             -_|_-")
        SLog.LogCritical ("            -_|_- /!\\          /!\\ -_|_-")
        SLog.LogCritical ("                      ! exit !")
        SLog.LogCritical ("            -_|_- \\|/          \\|/ -_|_-")
        SLog.LogCritical ("      -_|_-                             -_|_-")
        SLog.LogCritical ("-_|_-                                         -_|_-")
        sys.exit(1)

    else:
      savePath   = os.path.dirname ( Options['name'] )
      nameFile   = os.path.basename( Options['name'] )
    
      SLog.LogInfo ("file name   : [{}]".format( nameFile ) )
      SLog.LogInfo ("file path   : [{}]".format( savePath ) )   

    torrentPath = "{}/{}".format( savePath, nameFile)

    # exit if not exist
    if not os.path.exists(torrentPath) :
        SLog.LogCritical ("not exist  : [{}]".format( torrentPath ))
        SLog.LogCritical ("-_|_-")
        SLog.LogCritical ("      -_|_- ")
        SLog.LogCritical ("            -_|_- /!\\ exit !! /!\\ ")
        SLog.LogCritical ("            -_|_-  ")
        SLog.LogCritical ("      -_|_- ")
        SLog.LogCritical ("-_|_-")
        sys.exit(1)

    # If folder
    if os.path.isdir( torrentPath ):
      
      # find delete files
      deletefiles (recursive_glob(torrentPath, rlist['DeleteFiles']) )

      # SLog.LogInfo ("Files: [{}]".format(torrentPath))
      SLog.LogInfo ("Files...")
      fchange ( [ (dirpath, f) for dirpath, dirnames, filenames in os.walk( torrentPath ) for f in filenames ] )

      # SLog.LogInfo ("torrentPath : [{}]".format( torrentPath ) )
      # SLog.LogInfo ("savePath    : [{}]".format( savePath ) )
      # SLog.LogInfo ("nameFile    : [{}]".format( nameFile ) )
      # SLog.LogInfo ("files       : [{}]".format( files ) )

      # move single file to parent folder
      if Options['rmovsgl'] and sum([len(files) for r, d, files in os.walk( torrentPath )]) ==1:
        SLog.LogInfo ("Single file...." )
        mvfile(torrentPath)

        # delete path
        SLog.LogInfo ("Remove dir  : [{}]".format( torrentPath ) )
        os.rmdir( torrentPath )

      else:
        # rname folder ...
        SLog.LogInfo ("Dirs....")
        fchange ( [( savePath, nameFile )] )

    else:
      SLog.LogInfo ("File        : [{}], [{}]".format( savePath, nameFile ))
      # SLog.LogInfo ("File           : [{}], [{}]".format( os.path.dirname ( torrentPath ), os.path.basename(torrentPath) ))
      # fchange ( [( os.path.dirname ( torrentPath ), os.path.basename(torrentPath) )] )
      fchange ( [( savePath, nameFile )] )

  except Exception as e:
    ExceptionMessage = "({}) !!! Stop on error !!! line ({}) [{}] {}".format (
                      sys._getframe().f_code.co_name, 
                      sys.exc_info()[2].tb_lineno, 
                      type (e).__name__, 
                      str (e) )

    SLog.LogCritical (ExceptionMessage)
    SLog.LogCritical ("-_|_-                                         -_|_-")
    SLog.LogCritical ("      -_|_-                             -_|_-")
    SLog.LogCritical ("            -_|_- /!\\          /!\\ -_|_-")
    SLog.LogCritical ("                      ! exit !")
    SLog.LogCritical ("            -_|_- \\|/          \\|/ -_|_-")
    SLog.LogCritical ("      -_|_-                             -_|_-")
    SLog.LogCritical ("-_|_-                                         -_|_-")

    sys.exit(1)
