#! /usr/bin/env python3

# Script to save or restore all symlinks in a directory structure to a textfile 
# name: .symbolic-links.tree.txt
#
# swsymlinks dirkpetersen / Aug 2015
#

import sys, os, pwd, argparse, subprocess, re, time, datetime, tempfile

class KeyboardInterruptError(Exception): pass

def main():
    global args

    # Parse command-line arguments
    args = parse_arguments()

    oldcurrdir = os.getcwd()
    os.chdir(args.folder)
    currdir = os.getcwd() 
    curruser = pwd.getpwuid(os.getuid()).pw_name
    tmpdir = tempfile.gettempdir()

    if args.folder.startswith('./'):
        args.folder = args.folder[2:]

    if os.path.abspath(currdir) != os.path.abspath(args.folder):
        print("Current folder %s <> target folder %s, exiting....", (currdir,args.folder))
        return False

    if args.linkdbfolder and args.restore:
        print("You cannot use --linkdbfolder in --restore mode.")
        print("Please put .symbolic-links.tree.txt in the root of --folder")
        return False

    linkdbfolder = currdir
    if args.linkdbfolder:
        linkdbfolder = args.linkdbfolder
                
    fcnt=0
    dcnt=0    
    if args.save:
        print ('\nScanning folder %s to archive symlinks ...' % currdir)
        if args.single:
            # only create one single .symbolic-links.tree.txt at the root
                with open(os.path.join(linkdbfolder,".symbolic-links.tree.txt"),'w') as sfile:
                    dcnt+=1
                    for root, folders, files in mywalk(args.folder):
                        items=folders+files
                        for f in items:
                            try:
                                base=root.replace(currdir+'/','')
                                p=os.path.join(base,f)
                                if os.path.islink(p):
                                    stat=getstat(p)
                                    targ=os.readlink(p)
                                    sfile.write("%s|%s|%s\n" % (p,targ,stat.st_mtime))
                                    fcnt+=1
                                    if args.debug:
                                        sys.stderr.write('SYMLINK:%s\n   TARGET:%s\n' % (p,targ))
                                    
                            except Exception as err:
                                sys.stderr.write(str(err))
                                sys.stderr.write('\n')

        else:
            # create a .symbolic-links.tree.txt in each folder recursively
            for root, folders, files in mywalk(args.folder):
                try:
                    base=root.replace(currdir+'/','')
                    treefile=os.path.join(base,'.symbolic-links.tree.txt')
                    if os.path.exists(treefile):
                        os.remove(treefile)
                    oldroot=''
                except Exception as err:
                    sys.stderr.write(str(err))
                    sys.stderr.write('\n')
                items=folders+files
                for f in items:
                    try:
                        p=os.path.join(base,f)
                        if os.path.islink(p):
                            if oldroot != root:
                                dcnt+=1
                                oldroot=root
                                sys.stderr.write('Symlink Store: %s\n' % (treefile))
                            stat=getstat(p)
                            targ=os.readlink(p)
                            with open(os.path.join(root,'.symbolic-links.tree.txt'),'a') as sfile:
                                sfile.write("%s|%s|%s\n" % (f,targ,stat.st_mtime))
                            fcnt+=1
                            if args.debug:
                                sys.stderr.write('  SYMLINK:%s\n    TARGET:%s\n' % (p,targ))

                    except Exception as err:
                        sys.stderr.write(str(err))
                        sys.stderr.write('\n')
                    
        print("saved %i symlinks into %i .symbolic-links.tree.txt store(s)" % (fcnt, dcnt))

        
    elif args.clean:
        # remove all .symbolic-links.tree.txt files recursively
        cnt=0
        print ('recursively clean .symbolic-links.tree.txt from %s' % currdir)
        for root, folders, files in mywalk(args.folder):            
            if args.debug:
                print ("cleaning folder %s" % root)
            p=os.path.join(root,'.symbolic-links.tree.txt')
            if os.path.exists(p):
                os.remove(p)
                print('deleted %s' % p)                
                cnt+=1
        print('%i .symbolic-links.tree.txt file(s) have been removed.' % cnt)
        
    elif args.restore:
        for root, folders, files in mywalk(args.folder):
            base=root.replace(currdir+'/','')
            treefile=os.path.join(base,'.symbolic-links.tree.txt')
            if os.path.exists(treefile):
                sys.stderr.write('restoring from Symlink Store: %s ...\n ' % (treefile))
                dcnt+=1
                lines=[]
                with open(treefile,'r') as sfile:
                    lines=sfile.readlines()
                for line in lines:
                    try:
                        link,targ,mtime=line.split('|')                    
                        d=os.path.dirname(link)
                        if d:
                            #link was saved with a directory in .symbolic-links.tree.txt
                            if not os.path.exists(d):
                                os.makedirs(d)
                        else:
                            #link was saved as a file only in .symbolic-links.tree.txt
                            link=os.path.join(base,link)
                        if os.path.islink(link) and args.force:
                            os.unlink(link)
                        if not os.path.exists(link):
                            os.symlink(targ,link)
                            stat=getstat(link)
                            #set both symlink atime and mtime to mtime
                            os.utime(link,(float(mtime),float(mtime)),follow_symlinks=False)
                            fcnt+=1
                            if args.debug:
                                sys.stderr.write('SYMLINK:%s\n   TARGET:%s\n' % (link,targ))
                        else:
                            print('  skipping restore of link %s. File already exists' % link)
                    except Exception as err:
                        sys.stderr.write(str(err))
                        sys.stderr.write('\n')
        print("Restored %i symlinks from %i .symbolic-links.tree.txt store(s)" % (fcnt, dcnt))
    else:
        print("You need to use either --save, --save --single, --clean or --restore as a command option")

    os.chdir(oldcurrdir)
        

def startswithpath(pathlist, pathstr):
    """ checks if at least one of the paths in a list of paths starts with a string """
    for path in pathlist:
        if (os.path.join(pathstr, '')).startswith(path):
            return True
    return False

def getstartpath(pathlist, pathstr):
    """ return the path from pathlist that is the first part of pathstr"""
    for path in pathlist:
        if (os.path.join(pathstr, '')).startswith(path):
            return path
    return ''

                
def getstat(path):
    """ returns the stat information of a file"""
    statinfo=None
    try:
        statinfo=os.lstat(path)
    except (IOError, OSError) as e:   # FileNotFoundError only since python 3.3
        if args.debug:
            sys.stderr.write(str(e))
    except:
        raise
    return statinfo

def setfiletime(path,attr="atime"):
    """ sets the a time of a file to the current time """
    try:
        statinfo=getstat(path)
        if attr=="atime" or attr=="all":
            os.utime(path,(time.time(),statinfo.st_atime))
        if attr=="mtime" or attr=="all":
            os.utime(path,(time.time(),statinfo.st_mtime))        
        return True
    except Exception as err:
        sys.stderr.write(str(err))
        sys.stderr.write('\n')
        return False

def uid2user(uidNumber):
    """ attempts to convert uidNumber to username """
    import pwd
    try:
        return pwd.getpwuid(int(uidNumber)).pw_name
    except Exception as err:
        sys.stderr.write(str(err))
        sys.stderr.write('\n')
        return str(uidNumber)

def list2file(mylist,path):
    """ dumps a list into a text file, one line per item"""
    try:
        with open(path,'w') as f:
            for item in mylist:
                f.write("{}\r\n".format(item))
        return True
    except Exception as err:
        sys.stderr.write(str(err))
        sys.stderr.write('\n')
        return False

def pathlist2file(mylist,path,root):
    """ dumps a list into a text file, one line per item, but removes
         a root folder from all paths. Used for --files-from feature in rsync"""
    try:
        with open(path,'w') as f:
            for item in mylist:
                f.write("{}\r\n".format(item[len(root):]))
        return True
    except Exception as err:
        sys.stderr.write(str(err))
        sys.stderr.write('\n')
        return False

def mywalk(top, skipdirs=['.snapshot',]):
    """ returns subset of os.walk  """
    for root, dirs, files in os.walk(top,topdown=True,onerror=walkerr): 
        for skipdir in skipdirs:
            if skipdir in dirs:
                dirs.remove(skipdir)  # don't visit this directory 
        yield root, dirs, files 

def walkerr(oserr):    
    sys.stderr.write(str(oserr))
    sys.stderr.write('\n')
    return 0


def parse_arguments():
    """
    Gather command-line arguments.
    """
    parser = argparse.ArgumentParser(prog='swsymlinks',
        description='save or restore all symlinks in a directory structure' +\
               'to a textfile .symbolic-links.tree.txt')
    parser.add_argument( '--save', '-s', dest='save', action='store_true',
        help='save all symlinks to a text file',
        default=False )
    parser.add_argument( '--single', '-n', dest='single', action='store_true',
        help='save all symlinks into a single file .symbolic-links.tree.txt at the root',
        default=False )         
    parser.add_argument( '--clean', '-c', dest='clean', action='store_true',
        help='delete all .symbolic-links.tree.txt files recursively',
        default=False ) 
    parser.add_argument( '--restore', '-r', dest='restore', action='store_true',
        help='restore all symlinks from a text file',
        default=False )
    parser.add_argument( '--force', '-o', dest='force', action='store_true',
        help='force restore, even if a symlink already exists.',
        default=False )    
    parser.add_argument( '--debug', '-g', dest='debug', action='store_true',
        help='print the symlink targets to STDERR',
        default=False )        
    parser.add_argument( '--linkdbfolder', '-l', dest='linkdbfolder',
        action='store', 
        help='set folder location for .symbolic-links.tree.txt file')    
    parser.add_argument( '--folder', '-f', dest='folder',
        action='store', 
        help='search this folder and below for files to remove')
    args = parser.parse_args()
    if not args.folder:
        parser.error('required option --folder not given !')
    if args.debug:
        print('DEBUG: Arguments/Options: %s' % args)    
    return args

if __name__ == '__main__':
    sys.exit(main())
