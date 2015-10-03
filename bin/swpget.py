#!/usr/bin/env python3

# get multisegment swift files in parallel

import sys,os,getopt,json
import time

import multiprocessing

import swiftclient

def create_sparse_file(filename,length):
   #print("creating sparse file",filename)
   with open(filename, "wb") as f:
      f.truncate(length)

swift_auth_token=os.environ.get("OS_AUTH_TOKEN")
storage_url=os.environ.get("OS_STORAGE_URL")

def create_sw_conn():
   global swift_auth_token,storage_url

   if swift_auth_token and storage_url:
      return swiftclient.Connection(preauthtoken=swift_auth_token,
         preauthurl=storage_url)

   swift_auth=os.environ.get("ST_AUTH")
   swift_user=os.environ.get("ST_USER")
   swift_key=os.environ.get("ST_KEY")

   if swift_auth and swift_user and swift_key:
      return swiftclient.Connection(authurl=swift_auth,user=swift_user,
         key=swift_key)

   print("Error: Swift environment not configured!")
   sys.exit()

def parseSwiftUrl(path):
    path = path.lstrip('/')
    components = path.split('/');
    container = components[0];
    obj = '/'.join(components[1:])
    return container, obj

# container, object, offset, dest
def assemble_ms_object(x):
   #print("assembling",x) 
   conn=create_sw_conn()

   headers,body=conn.get_object(x[0],x[1])
   #print("body len=",len(body))
   with open(x[3],"r+b") as f_out:
      if x[2]>0:
         f_out.seek(x[2])
      f_out.write(bytes(body))

   conn.close()

def get_ms_object(sc,container,object,pool_size):
   #print("multisegment object",object)
   segments=[]
   segment_total=0

   # build segment map for parallel download
   headers,body=sc.get_object(container,object,
      query_string='multipart-manifest=get')
   manifest=json.loads(body.decode())
   dest=os.path.basename(object)
   for segment in manifest:
      segment_container,segment_obj=parseSwiftUrl(segment['name'])
      # store segment container, object and offset
      segments.append([segment_container,segment_obj,segment_total,dest])
      segment_total=segment_total+segment['bytes']

   # create sparse file
   create_sparse_file(dest,segment_total)

   # sequential assembly
   #for seg in segments:
   #   assemble_ms_object(seg)

   # parallel assembly
   #print("parallel assembly with",pool_size,"workers")
   p=multiprocessing.Pool(pool_size)
   p.map(assemble_ms_object,segments)

def get_object(conn,container,object):
   headers,body=conn.get_object(container,object)
   with open(os.path.basename(object),"w+b") as f_out:
      f_out.write(bytes(body))

def set_time(headers,name):
   if headers:
      if 'x-object-meta-mtime' in headers:
         mmt=int(float(headers['x-object-meta-mtime']))
      else:
         mkt=time.mktime(time.strptime(headers['last-modified'],
            "%a, %d %b %Y %X %Z"))
         mmt=int(time.mktime(time.localtime(mkt)))

      os.utime(os.path.basename(name),(mmt,mmt))

def get_objects(sc,container,object_list,pool_size):
   found=0
   #print("getting",object_list,"from container",container)

   try:
      headers,objs=sc.get_container(container,full_listing=True)
      for obj in objs:
         #print("found",obj['name'])
         if obj['name'] in object_list:
            #print("matched",obj['name'])
            found=found+1
            try:
               headers=sc.head_object(container, obj['name'])
            except:
               headers=[]
           
            if 'x-static-large-object' in headers:
               get_ms_object(sc,container,obj['name'],pool_size)
            else:
               get_object(sc,container,obj['name'])

            set_time(headers,obj['name'])

      if not found:
         print("No matching files found")

   except swiftclient.ClientException:
      print("Error: cannot access Swift container '%s'!" % container)

   sc.close()

def validate_dir(path,param):
   if not os.path.isdir(path):
      print("Error: %s '%s' is not accessible!" % (param,path))
      sys.exit()

   if path[-1]=='/':
      path=path[:-1] 

   return(path)

def usage():
   print("swpget [parameters]")
   print("Parameters:")
   print("\t-l local_directory (default .)")
   print("\t-c container (required)")
   print("\t-p pool_size (default 5)")
   print("\t-a auth_token (default OS_AUTH_TOKEN)")
   print("\t-s storage_url (default OS_STORAGE_URL)")

def main(argv):
   global swift_auth_token
   global storage_url

   container=""
   pool_size=5

   try:
      opts,args=getopt.getopt(argv,"l:c:p:a:s:h")
   except getopt.GetoptError:
      usage()
      sys.exit()

   for opt,arg in opts:
      if opt in ("-h"):
         container=""
         break
      elif opt in ("-l"): # override default local directory
         local_dir=validate_dir(arg,"local")
         os.chdir(local_dir)
      elif opt in ("-c"): # set container
         container=arg
      elif opt in ("-p"): # parallel workers
         pool_size=int(arg)
      elif opt in ("-a"): # override swift_auth_token
         swift_auth_token=arg
      elif opt in ("-s"): # override storage URL
         storage_url=arg

   if not container or not args:
      usage()
   else:
      sc=create_sw_conn()
      if sc:
         get_objects(sc,container,args,pool_size)

if __name__ == '__main__':
   main(sys.argv[1:])
