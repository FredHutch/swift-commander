#!/usr/bin/env python3

import os,sys,getopt,tarfile
import getpass

from distutils.spawn import find_executable

import time
import socket
import optparse
import subprocess
import multiprocessing

from swiftclient import Connection

from swiftclient import shell
from swiftclient import RequestException
from swiftclient.exceptions import ClientException
from swiftclient.multithreading import OutputManager

# swiftclient 3.2+ support
import swiftclient
from pkg_resources import parse_version
import argparse

try:
    from scandir import walk
except:
    from os import walk

swift_auth=os.environ.get("ST_AUTH")
swift_auth_token=os.environ.get("OS_AUTH_TOKEN")
storage_url=os.environ.get("OS_STORAGE_URL")
haz_pigz=False

# define minimum parser object(s) to allow swiftstack shell to run 
# old is pre swiftclient 3.1 and new is 3.1+

def shell_old_minimal_options():
   global swift_auth,swift_auth_token,storage_url

   parser = optparse.OptionParser()

   parser.add_option('-A', '--auth', dest='auth',
      default=swift_auth)
   parser.add_option('-V', '--auth-version',
      default=os.environ.get('ST_AUTH_VERSION',
         (os.environ.get('OS_AUTH_VERSION','1.0'))))
   parser.add_option('-U', '--user', dest='user',
      default=os.environ.get('ST_USER'))
   parser.add_option('-K', '--key', dest='key',
      default=os.environ.get('ST_KEY'))

   parser.add_option('--os_auth_token',default=swift_auth_token)
   parser.add_option('--os_storage_url',default=storage_url)

   parser.add_option('--os_username')
   parser.add_option('--os_password')
   parser.add_option('--os_auth_url')

   parser.add_option('--os_user_id')
   parser.add_option('--os_user_domain_id')
   parser.add_option('--os_user_domain_name')
   parser.add_option('--os_tenant_id')
   parser.add_option('--os_tenant_name')
   parser.add_option('--os_project_id')
   parser.add_option('--os_project_domain_id')
   parser.add_option('--os_project_name')
   parser.add_option('--os_project_domain_name')
   parser.add_option('--os_service_type')
   parser.add_option('--os_endpoint_type')
   parser.add_option('--os_region_name')

   # new mandatory bogosity required for swiftclient >= 3.0.0
   parser.add_option('--debug')
   parser.add_option('--info')
   
   parser.add_option('-v', '--verbose', action='count', dest='verbose',
       default=1, help='Print more info.')

   return parser

def shell_new_minimal_options():
   global swift_auth,swift_auth_token,storage_url

   parser = argparse.ArgumentParser()

   parser.add_argument('-A', '--auth', dest='auth',
      default=swift_auth)
   parser.add_argument('-V', '--auth-version',
      default=os.environ.get('ST_AUTH_VERSION',
         (os.environ.get('OS_AUTH_VERSION','1.0'))))
   parser.add_argument('-U', '--user', dest='user',
      default=os.environ.get('ST_USER'))
   parser.add_argument('-K', '--key', dest='key',
      default=os.environ.get('ST_KEY'))

   parser.add_argument('--os_auth_token',default=swift_auth_token)
   parser.add_argument('--os_storage_url',default=storage_url)

   parser.add_argument('--os_username')
   parser.add_argument('--os_password')
   parser.add_argument('--os_auth_url')

   parser.add_argument('--os_user_id')
   parser.add_argument('--os_user_domain_id')
   parser.add_argument('--os_user_domain_name')
   parser.add_argument('--os_tenant_id')
   parser.add_argument('--os_tenant_name')
   parser.add_argument('--os_project_id')
   parser.add_argument('--os_project_domain_id')
   parser.add_argument('--os_project_name')
   parser.add_argument('--os_project_domain_name')
   parser.add_argument('--os_service_type')
   parser.add_argument('--os_endpoint_type')
   parser.add_argument('--os_region_name')

   # new mandatory bogosity required for swiftclient >= 3.0.0
   parser.add_argument('--debug')
   parser.add_argument('--info')
   
   parser.add_argument('-v', '--verbose', action='count', dest='verbose',
       default=1, help='Print more info.')

   # even more options required in later versions of swift 3.x
   parser.add_argument('--os_auth_type')
   parser.add_argument('--os_application_credential_id')
   parser.add_argument('--os_application_credential_secret')
   parser.add_argument('--prompt', action='store_true', dest='prompt', default=False)

   return parser

# check for swiftclient version and point to appropriate shell options
if parse_version(swiftclient.__version__)<parse_version('3.1.0'):
   shell_minimal_options = shell_old_minimal_options
else:
   shell_minimal_options = shell_new_minimal_options

# wrapper function for swiftstack shell functions
def sw_shell(sw_fun,*args):
   global swift_auth_token,storage_url

   if swift_auth_token and storage_url:
      args=args+("--os_auth_token",swift_auth_token,
         "--os_storage_url",storage_url)

   args = ('',) + args
   with OutputManager() as output:
      parser = shell_minimal_options()
      try:
         sw_fun(parser, list(args), output)
      except (ClientException, RequestException, socket.error) as err:
         output.error(str(err))
 
def sw_download(*args):
   sw_shell(shell.st_download,*args)
 
def sw_upload(*args):
   sw_shell(shell.st_upload,*args)
 
def sw_post(*args):
   sw_shell(shell.st_post,*args)
 
# suffix of archive files
tar_suffix=".tar.gz"
root_id=".root"

# True if 1st char of path member is '.' else False
def is_hidden_dir(dir_name):
   for item in dir_name.split('/'):
      if item[0]=='.':
         return True

   return False

def print_flush(str):
   sys.stdout.write(str+'\n')
   sys.stdout.flush()

# apparently getpid is ok because it's different between mp tasks
def unique_id():
   return str(os.getpid())

def create_tar_file(filename,src_path,file_list,recurse=False):
   global haz_pigz

   # only archive src_path directory
   tar_params=["tar","cvf",filename,"--directory="+src_path]
   if not recurse:
      tar_params+=["--no-recursion"]
   if haz_pigz:
      tar_params+=["--use-compress-program=pigz"]

   # include directory itself in archive for ownership & permissions
   tar_params=tar_params+['.']

   # generate external file list only if files to be archived
   if file_list:
      tmp_file="/tmp/.tar."+unique_id()
      with open(tmp_file,"w") as f:
         for file in file_list:
            f.write("-- \""+file+"\"\n")
      tar_params+=["-T",tmp_file]
  
   ret=subprocess.call(tar_params)
   if ret>0:
      sys.stderr.write('***** TAR ERROR %s, command: %s *****\n' % 
         (ret,tar_params))   

   if file_list:
      os.unlink(tmp_file)

def upload_file_to_swift(filename,swiftname,container,meta):
   final=[container,filename]
   if meta:
      final=meta+final

   sw_upload("--object-name="+swiftname,
      "--segment-size=2147483648",
      "--use-slo",
      "--segment-container=.segments_"+container,
      "--header=X-Object-Meta-Uploaded-by:"+getpass.getuser(),*final)

def archive_tar_file(src_path,file_list,container,tmp_dir,pre_path,meta,
   recurse=False):
   global tar_suffix

   # archive_name is name for archived object
   archive_name=pre_path+tar_suffix
   # temp_archive_name is name of local tar file
   temp_archive_name=unique_id()+os.path.basename(archive_name)
   if tmp_dir:
      temp_archive_name=os.path.join(tmp_dir,temp_archive_name)
  
   # Create local tar file 
   create_tar_file(temp_archive_name,src_path,file_list,recurse)

   # Upload tar file to container as 'archive_name' 
   upload_file_to_swift(temp_archive_name,archive_name,container,meta)

   # Delete local tar file
   os.unlink(temp_archive_name)

def is_child_or_sib(dir_name,last_dir):
   dname=os.path.dirname(dir_name) 
   return (dname==last_dir or dname==os.path.dirname(last_dir))

# param order: [src_path,file_list,container,tmp_dir,pre_path,meta]
def archive_worker(item):
   archive_tar_file(*item)

# if par==1 then multiprocessing Pool won't actually be used (debug mostly)
def archive_to_swift(local_dir,container,no_hidden,tmp_dir,prefix,par,subtree,
   meta):
   last_dir=""
   special=['.git']

   # Now updating object not container metadata
   #sw_post(container,*meta)
   sw_post(container)

   archive_pool=multiprocessing.Pool(par)

   for dir_name, subdir_list, file_list in mywalk(local_dir):
      rel_path=os.path.relpath(dir_name,local_dir)
      if (not (no_hidden and is_hidden_dir(rel_path))):
         # if files in root directory use basename of root
         if rel_path==".":
            rel_path=os.path.basename(dir_name)+root_id

         dir_t=dir_name.split('/')
         if dir_t[-1] in special:
            # special directory - archive recursively from here
            #print("\tlast is in special!")
            archive_worker([dir_name,file_list,container,tmp_dir,
               os.path.join(prefix,rel_path),meta,True])
         elif any(item in special for item in dir_t):
            # assumed child of special path, ignore as archived from special
            #print("\tskipping child of special!")
            pass
         elif (not subtree) or (is_subtree(subtree,dir_name)):
            p=[dir_name,file_list,container,tmp_dir,
               os.path.join(prefix,rel_path),meta]
            if par>1:
               archive_pool.apply_async(archive_worker,[p])
            else:
               archive_worker(p)

         last_dir=dir_name

   archive_pool.close()
   archive_pool.join()

# parse name into directory tree
def create_local_path(local_dir,archive_name):
   global tar_suffix

   path=os.path.join(local_dir,archive_name)
   if path.endswith(tar_suffix):
      path=path[:-len(tar_suffix)]

   if not os.path.exists(path):
      os.makedirs(path)
   
   return path

def create_sw_conn():
   global swift_auth,swift_auth_token,storage_url

   if swift_auth_token and storage_url:
      return Connection(preauthtoken=swift_auth_token,preauthurl=storage_url)

   if swift_auth:
      swift_user=os.environ.get("ST_USER")
      swift_key=os.environ.get("ST_KEY")

      if swift_user and swift_key:
         return Connection(authurl=swift_auth,user=swift_user,key=swift_key)

   print("Error: Swift environment not configured!")
   sys.exit()

def extract_tar_file(tarfile,termpath):
   global haz_pigz

   tar_params=["tar","xvf",tarfile,"--directory="+termpath,
        '--same-permissions', '--delay-directory-restore'] 
        # --same-owner is used when user=root
   if haz_pigz:
      tar_params+=["--use-compress-program=pigz"]

   ret=subprocess.call(tar_params)
   if ret > 0:
      sys.stderr.write('***** TAR ERROR %s, command: %s *****\n' % 
         (ret,tar_params))
   
def retrieve_tar_file(tmp_dir,container,obj_name,local_dir,prefix):
   global tar_suffix
   global root_id

   # download tar file and extract into terminal directory
   temp_file=unique_id()+tar_suffix
   if tmp_dir:
      temp_file=os.path.join(tmp_dir,temp_file)

   sw_download("--output="+temp_file,container,obj_name)

   # strip prefix and if next char is /, strip it too
   if prefix and obj_name.startswith(prefix):
      obj_name=obj_name[len(prefix):] 
      if obj_name[0]=='/':
         obj_name=obj_name[1:]
   
   # if bundle, extract using tar embedded paths
   if obj_name.endswith(root_id+tar_suffix):
      term_path=local_dir
   else:
      term_path=create_local_path(local_dir,obj_name)

   extract_tar_file(temp_file,term_path)

   os.unlink(temp_file)

def extract_worker(item):
   retrieve_tar_file(*item)

# if par==1 then multiprocessing Pool won't actually be used (debug mostly)
def extract_to_local(local_dir,container,no_hidden,tmp_dir,prefix,par):
   global tar_suffix
   global root_id

   swift_conn=create_sw_conn()
   if swift_conn:
      try: 
         headers,objs=swift_conn.get_container(container,prefix=prefix,
            full_listing=True)

         extract_pool=multiprocessing.Pool(par)

         for obj in objs:
            if obj['name'].endswith(tar_suffix):
               if no_hidden and is_hidden_dir(obj['name']):
                  continue

               # param order: [tmp_dir,container,obj_name,local_dir,prefix]
               p=[tmp_dir,container,obj['name'],local_dir,prefix]
               if par>1:
                  extract_pool.apply_async(extract_worker,[p])
               else:
                  extract_worker(p)

         extract_pool.close()
         extract_pool.join()
      except ClientException:
         print("Error: cannot access Swift container '%s'!" % container)

      swift_conn.close()

def usage():
   print("archive [parameters]")
   print("Parameters:")
   print("\t-l local_directory (default .)")
   print("\t-c container (required)")
   print("\t-x (extract from container to local directory)")
   print("\t-n (no hidden directories)")
   print("\t-t temp_dir (directory for temp files)")
   print("\t-a auth_token (default OS_AUTH_TOKEN)")
   print("\t-s storage_url (default OS_STORAGE_URL)")
   print("\t-p prefix")
   print("\t-P parallel_instances (default 3)")
   print("\t-m name:value (set object metadata)")

# is path a child of tree?
def is_subtree(tree,path):
   tree_sp=tree.split('/')
   path_sp=path.split('/')

   if len(path_sp)<len(tree_sp):
      return False

   for t,p in zip(tree_sp,path_sp):
      if t!=p:
         return False

   return True

def validate_dir(path,param):
   if not os.path.isdir(path):
      print("Error: %s '%s' is not accessible!" % (param,path))
      sys.exit()

   if path[-1]=='/':
      path=path[:-1] 

   return(path)

def mywalk(top, skipdirs=['.snapshot']):
    """ returns subset of os.walk  """
    for root, dirs, files in walk(top,topdown=True,onerror=walkerr):
        for skipdir in skipdirs:
            if skipdir in dirs:
                dirs.remove(skipdir)  # don't visit this directory 
        yield root, dirs, files

def walkerr(oserr):
    sys.stderr.write(str(oserr))
    sys.stderr.write('\n')
    return 0

def main(argv=None):
   global swift_auth_token
   global storage_url
   global haz_pigz
   argv = argv or sys.argv[1:]

   meta=[]
   sub_tree=""
   local_dir="."
   container=""
   tmp_dir=""
   extract=False
   no_hidden=False
   prefix=""
   par=3

   try:
      opts,args=getopt.getopt(argv,"l:c:t:a:s:p:P:S:m:xnh")
   except getopt.GetoptError:
      usage()
      sys.exit()

   for opt,arg in opts:
      if opt in ("-h"):
         usage()
         sys.exit()
      elif opt in ("-l"): # override default local directory
         local_dir=validate_dir(arg,"local")
      elif opt in ("-c"): # set container
         container=arg
      elif opt in ("-t"): # temp file directory
         tmp_dir=validate_dir(arg,"tmp_dir")
      elif opt in ("-a"): # override auth_token
         swift_auth_token=arg
      elif opt in ("-s"): # override storage URL
         storage_url=arg
      elif opt in ("-p"): # set prefix
         prefix=arg
      elif opt in ("-P"): # set parallel threads
         par=int(arg)
      elif opt in ("-x"): # extract mode
         extract=True
      elif opt in ("-n"): # set no-hidden flag to skip .*
         no_hidden=True
      elif opt in ("-S"): # specify optional sub-tree
         sub_tree=validate_dir(os.path.join(local_dir,arg),"subtree")
      elif opt in ("-m"): # specify object metadata
         if arg.count(':')==1:
            meta.append("-HX-Object-Meta-"+arg)
         else:
            print("Error: metadata not in format key:value!")
            sys.exit()

   if not container:
      usage()
   else:
      if find_executable("pigz"):
         haz_pigz=True

      if extract:
         extract_to_local(local_dir,container,no_hidden,tmp_dir,prefix,par)
      else:
         archive_to_swift(local_dir,container,no_hidden,tmp_dir,prefix,par,
            sub_tree,meta)

if __name__=="__main__":
   main()
