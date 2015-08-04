#!/usr/bin/env python3

# proof-of-concept to get multisegment swift files in parallel
# missing method for getting swift objects as streams to feed
# to existing assembly process

import sys,os,getopt,json

import multiprocessing

import swiftclient

seg_suffix=".seg"
container_name="assembly"

def create_segment_file(basename,length):
   print("creating segment",basename)
   with open(basename+seg_suffix, "w") as f:
      for i in range(0,length):
         f.write(basename)

def create_sparse_container(filename,length):
   print("creating sparse container",filename)
   with open(filename, "wb") as f:
      f.truncate(length)

segs="abcdefghijklmnopqrstuvwxyz"
seg_size=10000
pool_size=5

def assembler(x):
   offset=segs.index(x)
   with open(container_name,"r+b") as f_out:
      f_out.seek(offset*seg_size)
      with open(x+seg_suffix,"r") as f_in:
         c=f_in.read()
         f_out.write(bytes(c,'UTF_8'))

def assembly_test():
   # create segment files
   for seg in segs:
      create_segment_file(seg,seg_size)

   # create sparse container
   create_sparse_container(container_name,len(segs)*seg_size)

   # try it serially first
   #print("serial assembly")
   #for seg in segs:
   #   assembler(seg)

   # launch parallel workers to assemble segment files into container
   print("parallel assembly with",pool_size,"workers")
   p=multiprocessing.Pool(pool_size)
   p.map(assembler,segs)

swift_auth=os.environ.get("ST_AUTH")

def create_sw_conn():
   global swift_auth

   swift_user=os.environ.get("ST_USER")
   swift_key=os.environ.get("ST_KEY")

   if swift_auth and swift_user and swift_key:
      return swiftclient.Connection(authurl=swift_auth,user=swift_user,key=swift_key)

   print("Error: Swift environment not configured!")

def parseSwiftUrl(path):
    path = path.lstrip('/')
    components = path.split('/');
    container = components[0];
    obj = '/'.join(components[1:])
    return container, obj

def get_ms_object(sc,container,object):
   print("multisegment object",object)
   segments=[]
   segment_total=0

   # build segment map for parallel download
   headers,body=sc.get_object(container,object,
      query_string='multipart-manifest=get')
   manifest=json.loads(body.decode())
   for segment in manifest:
      #print("full segment",segment)
      #print("segment %s" % segment['name'])
      segment_container,segment_object=parseSwiftUrl(segment['name'])
      #print("segCon",segment_container,"segObj",segment_object)
      # store segment container, object and offset
      segments.append([segment_container,segment_object,segment_total)
      segment_total=segment_total+segment['bytes']

   # create sparse container
   create_sparse_container(object,segment_total)

def get_objects(container,object_list):
   print("getting",object_list,"from container",container)

   sc=create_sw_conn()
   if sc:
      try:
         headers,objs=sc.get_container(container)
         for obj in objs:
            if obj['name'] in object_list:
               print("found",obj['name'])
               try:
                  headers=sc.head_object(container, obj['name'])
               except:
                  headers=[]
               if 'x-static-large-object' in headers:
                  get_ms_object(sc,container,obj['name'])
               else:
                  print("single object")

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
   print("spget [parameters]")
   print("Parameters:")
   print("\t-l local_directory (default .)")
   print("\t-c container (required)")

def main(argv):
   container=""

   try:
      opts,args=getopt.getopt(argv,"l:c:t:b:a:p:P:xnh")
   except getopt.GetoptError:
      usage()
      sys.exit()

   for opt,arg in opts:
      if opt in ("-h"):
         container=""
         break
      elif opt in ("-l"): # override default local directory
         local_dir=validate_dir(arg,"local")
      elif opt in ("-c"): # set container
         container=arg

   if not container or not args:
      usage()
   else:
      get_objects(container,args)

if __name__ == '__main__':
   main(sys.argv[1:])
   #assembly_test()
