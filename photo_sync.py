#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import sys
import shutil
import collections
import hashlib

def usage():
    print >>sys.stderr, "photo_sync.py"
    print >>sys.stderr, "Nick Lambourne 2013, done on a Chomebook running Ubuntu. After a glass of wine. Or 2."
    print >>sys.stderr
    print >>sys.stderr, "Usage: photo_sync.py [options]"
    print >>sys.stderr
    print >>sys.stderr, "    -s, --storage         Location of the photo storage directory"
    print >>sys.stderr, "    -c, --camera          Location of the camera memory card directory"
    print >>sys.stderr, "    -g, --staging         Location of the staging directory (where the files get copied to)"
    print >>sys.stderr, "                          This should be inside the storage location ideally"
    print >>sys.stderr, "    -q, --quiet           Quiet mode, no output"
    print >>sys.stderr, "    -cp, --checkphoto     Check the photo disk for conflicts"
    print >>sys.stderr, "                          This ensures that all photos are unique in name and are not duplicated in directories"
    print >>sys.stderr, "    -cmp,--checkmemphoto  Check that there are no conflicts on the memory card and the photo disk"
    print >>sys.stderr, "                          This ensures that all photos are unique over all the cards"    
    sys.exit(1)


def get_options():
    class Options:
        def __init__(self):
            self.storage = None
            self.camera = None
            self.staging = None
            self.quiet = False
            self.check_for_photo_disk_conflicts = False
            self.check_for_memory_photo_conflicts = False

    options = Options()
    a = 1
    while a < len(sys.argv):
        if sys.argv[a].startswith("-"):
            if sys.argv[a] in ("-s", "--storage"):
                a += 1
                options.storage = sys.argv[a]
            elif sys.argv[a] in ("-c", "--camera"):
                a += 1
                options.camera = sys.argv[a]      
            elif sys.argv[a] in ("-g", "--staging"):
                a += 1
                options.staging = sys.argv[a]                                  
            elif sys.argv[a] in ("-q", "--quiet"):
                options.quiet = True
            elif sys.argv[a] in ("-cp", "--checkphoto"):
                options.check_for_photo_disk_conflicts = True
            elif sys.argv[a] in ("-cmp", "--checkmemphoto"):
                options.check_for_memory_photo_conflicts = True            
            else:
                usage()
        else:
            usage()
        a += 1

    if options.storage == None or options.camera == None:
        usage()

    return options


###################################################
## Create a list of Photos in a directory
###################################################
def get_photo_list_from_path(path):
    class Photo:
        def __init__(self, filename, path, size):
            self.filename = filename
            self.path = path
            self.size = size
            
        def __str__(self):
            return self.filename + "_" + str(self.size)
        
        def __gt__(self, photo2):
            return cmp( str(self), str(photo2) )
        
        def __eq__(self, photo2):
            return cmp( str(self), str(photo2) )     
        
        def __hash__(self):
            return hash(str(self))

    file_list = []
    for root, subFolders, files in os.walk(path):
        for file in files:
            p = Photo( file, root, os.path.getsize(os.path.join(root,file)) )
            file_list.append( p )    
    return file_list


###################################################
## Find duplicate file names in a Photo list
###################################################
def find_duplicate_file_names( file_list ):
    #make a list of just the
    just_name = [] 
    for f in file_list:
        just_name.append( f.filename )
    return [x for x, y in collections.Counter(just_name).items() if y > 1]


###################################################
## get file checksum
###################################################
def get_file_checksum( filename ):
    with open(filename, 'rb') as fh:
        m = hashlib.md5()
        while True:
            data = fh.read(8192)
            if not data:
                break
            m.update(data)
        return m.hexdigest()


###################################################
## Dup photos func
###################################################
def find_duplicate_picture_storage_files( picture_storage_files ):
    #class containing the file name and a dict of the checksums
    #stored this way to make pasing easier...
    class DuplicatePic:
        def __init__( self, filename ):
            self.filename = filename
            self.file_paths_indexed_by_checksum = {}
            
        def add_file(self, file_path, checksum ):
            if self.file_paths_indexed_by_checksum.has_key(checksum) == False:                
                self.file_paths_indexed_by_checksum[checksum] = [] #initialse
            self.file_paths_indexed_by_checksum[checksum].append( file_path )
    
    #get the file names
    dup_photo_files = find_duplicate_file_names( picture_storage_files )
    dup_pics = []    
    
    #build up the list of DuplicatePic classes
    for dup in dup_photo_files:
        p = DuplicatePic(dup)
        for f in picture_storage_files:
            if f.filename == dup:
                file_path = os.path.join( f.path, f.filename )
                p.add_file( file_path, get_file_checksum( file_path) )
        dup_pics.append( p )

    return dup_pics


###################################################
## Main!
###################################################
if __name__ == '__main__':
    
    #parse options
    options = get_options()
    
    #get the file lists
    picture_storage_files = get_photo_list_from_path(options.storage)
    memory_card_files = get_photo_list_from_path(options.camera)
    
    if options.quiet == False:
        print len(picture_storage_files), "images in picture storage"
        print len(memory_card_files), "images in camera card" 
    
    #get the delta in directories
    memory_card_files_that_need_updating = list(set(memory_card_files) - set(picture_storage_files)) 

    print "Files missing from the storage directory:", len(memory_card_files_that_need_updating)
    
    #optionally print out all the files that are about to be copied
    #useful for debug when the staging directory isn' specified.
    #yes, I don't like behavior like this (operation defined by obmitting parameters instead 
    #of explicit options, but hey ho...)
    if options.quiet == False and len(memory_card_files_that_need_updating) != 0:
        print "Files that need updating are:"
        print sorted(memory_card_files_that_need_updating)
    
    #if the staging dir is specified, copy the files over, preserving the data
    if options.staging != None:
        for fcopy in memory_card_files_that_need_updating:
            shutil.copy2(fcopy, options.staging )

    #if we are checking for duplicates on the photo disk, do so now
    if options.check_for_photo_disk_conflicts == True:        
        print "Checking duplicate pics - this can be very slow..."
        dup_pics = find_duplicate_picture_storage_files( picture_storage_files )
        print "Duplicate pictures on the photo storage:"
             
        #a little convoluted...
        #Now we have a list of all the duplicate pictures (list of type DuplicatePic)
        #iterate over it, deciding if the file is:
        #   (a) simply copied in multiple places
        #   (b) has a collision with the same name
        for f in dup_pics:
            if len(f.file_paths_indexed_by_checksum) == 1: #files that are all the same
                print f.filename, "appears in the following locations:"
                for path in f.file_paths_indexed_by_checksum.itervalues().next():
                    print "   - ", path
            else:
                print "There are multiple files named", f.filename, "but they do not have the same checksums"
                for check in sorted( f.file_paths_indexed_by_checksum ):
                    print "   - Checksum of:", check
                    for a in f.file_paths_indexed_by_checksum[check]:
                        print "      - ", a        

    sys.exit(0)
