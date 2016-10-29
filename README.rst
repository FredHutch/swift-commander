swift-commander
===============

swift commander (swc) is a wrapper to various command line client tools for openstack swift cloud
storage systems. The purpose of swc is 3 fold:

-  provide a very simple user interface to Linux users
-  provide a unified user interface to swiftclient, curl, etc with reasonable defaults
-  model commands after classic shell tools such as cd, ls, etc.

Basic Operations
================

if swc is invoked without any options it shows a basic help page:

::

    Swift Commander (swc) allows you to easily work with a swift object store.
    swc supports sub commands that attempt to mimic standard unix file system tools.
    These sub commands are currently implemented: (Arguments in square brackets are 
    optional).

      swc upload <src> <targ>   -  copy file / dirs from a file system to swift
      swc download <src> <targ> -  copy files and dirs from swift to a file system
      swc cd <folder>           -  change current folder to <folder> in swift
      swc ls [folder]           -  list contents of a folder - or the current one
      swc mkdir <folder>        -  create a folder (works only at the root)
      swc rm <path>             -  delete all file paths that start with <path>
      swc pwd                   -  display the current swift folder name
      swc cat|more|less <file>  -  download a file to TMPDIR and view with cat, more or less
      swc vi|emacs|nano <file>  -  download a file to TMPDIR and edit it with vi|emacs or nano
      swc chgrp <group> <fld.>  -  grant/remove rw access to current swift account or container
      swc rw <group> <folder>   -  add rw access to current swift account or container
      swc ro <group> <folder>   -  add ro access to current swift account or container
      swc publish|hide </fld.>  -  make root folder public (web server mode) or hide it
      swc list <folder> [filt]  -  list folder content (incl. subfolders) and filter
      swc search <str> <folder> -  search for a string in text files under /folder
      swc openwith <cmd> <file> -  download a file to TMPDIR and open it with <cmd>
      swc header <file>         -  display the header of a file in swift
      swc meta <file>           -  display custom meta data of a file in swift
      swc mtime <file>          -  show the original mtime of a file before uploaded
      swc size <folder>         -  show the size of a swift or a local folder
      swc compare <l.fld> <fld> -  compare size of a local folder with a swift folder
      swc hash <locfile> <file> -  compare the md5sum of a local file with a swift file
      swc arch <src> <targ>     -  create one tar archive for each folder level
      swc unarch <src> <targ>   -  restore folders that have been archived
      swc auth                  -  show current storage url and auth token
      swc env                   -  show authentication env vars (ST_ and OS_)
      swc clean                 -  remove current authtoken credential cache

    Examples:
      swc upload /local/folder /swift/folder
      swc upload --symlinks /local/folder /swift/folder (save symlinks)
      swc compare /local/folder /swift/folder
      swc download /swift/folder /scratch/folder
      swc download /swift/folder $TMPDIR
      swc rm /archive/some_prefix
      swc more /folder/some_file.txt
      swc openwith emacs /folder/some_file.txt

Important: What you need to know about the Swift architecture
-------------------------------------------------------------

-  swift does not know sub directories such as a file system. It knows containers and in containers
   it carries objects (which are actually files).
-  if you upload a path with many directory levels such as
   /folder1/folder2/folder3/folder4/myfile.pdf to swift it will cheat a little and put an object
   called ``folder2/folder3/folder4/myfile.pdf`` into a container called ``folder1``.
-  the object is just like a filename that contains a number of forward slashes. Forward slashes are
   allowed because swift does not know any directories and can have the / character as part of a
   filename. These fake folders are also called ``Pseudo-Hierarchical Directories`` (
   http://www.17od.com/2012/12/19/ten-useful-openstack-swift-features/ )
-  the architecture has advantages and disadvantages. An advantage is that you can retrieve hundreds
   of thousands of object names in a few seconds. The disadvantage is that a single container
   eventually reaches a scalability limit. Currently this limit is at about 2 million objects per
   container. You should not put more than 2 million files into a single container or /root\_folder.
-  swift commander (swc) allows you to ignore the fact that there are containers and pseudo folders.
   For the most part you can just treat them both as standard directories

Authentication
--------------

-  ``swc`` does not implement any authentication but uses a swift authentication environment, for
   example as setup by ``https://github.com/FredHutch/swift-switch-account`` including Active
   Directory integration.
-  if a swift authentication environment is found ``swc`` creates swift auth\_tokens on the fly and
   uses them with RESTful tools such as curl.

swc upload
~~~~~~~~~~

use ``swc upload /local_dir/subdir /my_swift_container/subfolder`` to copy data from a local or
networked posix file system to a swift object store. ``swc upload`` wraps ``swift upload`` of the
standard python swift client:

::

    joe@box:~/sc$ swc upload ./testing /test
    *** uploading ./test ***
    *** to Swift_Account:/test/ ***
    executing:swift upload --changed --segment-size=1073741824 --use-slo --segment-container=".segments_test" --header="X-Object-Meta-Uploaded-by:joe" --object-name="" "test" "./test"
    *** please wait... ***
    /fld11/file12
    /fld11/file11
    /fld11/fld2/fld3/fld4/file43
    /fld11/fld2/fld3/fld4/file42
    .

the swc wrapper adds the following features to ``upload``:

-  --segment-size ensures that uploads for files > 5GB do not fail. 1073741824 = 1GB
-  Uploaded-by metadata keeps track of the operating system user (often Active Directory user) that
   upload the data
-  setting --segment-container ensures that containers that carry the segments for multisegment
   files are hidden if users access these containers with 3rd. party GUI tools (ExpanDrive,
   Cyberduck, FileZilla) to avoid end user confusion
-  --slo stands for Static Large Object and SLO's the recommended object type for large objects /
   files.

as an addional feature you can add multiple metadata tags to each uploaded object, which is great
for retrieving archived files later:

::

    joe@box:~/sc$ swc upload ./test /test/example/meta project:grant-xyz collaborators:jill,joe,jim cancer:breast
    *** uploading ./test ***
    *** to Swift_Account:/test/example/meta ***
    executing:swift upload --changed --segment-size=1073741824 --use-slo --segment-container=".segments_test" --header="X-Object-Meta-Uploaded-by:petersen" --header=X-Object-Meta-project:grant-xyz --header=X-Object-Meta-collaborators:jill,joe,jim --header=X-Object-Meta-cancer:breast --object-name="example/meta" "test" "./test"
    *** please wait... ***
    example/meta/fld11/fld2/file21
    example/meta/fld11/file11
    .
    .
    /test/example/meta

These metadata tags stay in the swift object store with the data. They are stored just like other
important metadata such as change data and name of the object.

::

    joe@box:~/sc$ swc meta example/meta/fld11/file13
           Meta Cancer: breast
    Meta Collaborators: jill,joe,jim
      Meta Uploaded-By: petersen
          Meta Project: grant-xyz
            Meta Mtime: 1420047068.977197

if you store metadata tags you can later use an external search engine such as ElasticSearch to
quickly search for metadata you populated while uploading data

alias: you can use ``swc up`` instead of ``swc upload``

swc download
~~~~~~~~~~~~

use ``swc download /my_swift_container/subfolder /local/subfolder`` to copy data from a swift object
store to local or network storage. swc download\ ``wraps``\ swift download\` of the standard python
swift client:

::

    joe@box:~/sc$ swc download /test/example/ $TMPDIR/ 
    example/meta/fld11/fld2/file21
    example/meta/fld11/file11

alias: you can use ``swc down`` instead of ``swc download``

swc arch
~~~~~~~~

``swc arch`` is a variation of ``swc upload``. Instead of uploading the files as is, it creates a
tar.gz archive for each directory and uploads the tar.gz archives. swc arch is different from
default tar behavior because it does not create a large tar.gz file of an entire directory structure
as large tar.gz files are hard to manage (as one cannot easily navigate the directory structure
within or get quick access to a spcific file). Instead swc arch creates tar.gz files that do not
include sub directories and it creates a separate tar.gz file for each directory and directory
level. The benefit of this approach is that the entire directory structure remains intact and you
can easily navigate it by using ``swc cd`` and ``swc ls``

swc cd, swc, ls, swc mkdir
~~~~~~~~~~~~~~~~~~~~~~~~~~

these commands are simplified versions of the equivalent standard GNU tools and should work very
similar to these tools.

swc mtime
~~~~~~~~~

use ``swc mtime /my_swift_container/subfolder/file`` to see the modification time data from a swift
object store to local or network storage. ``swc download`` wraps ``swift download`` of the standard
python swift client:
