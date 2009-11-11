#!/bin/sh

# Build: works great
mem


# Change the included file
echo "I was included!\nI was included!" > included_file.tex
mem
# Build did work 

# Change the included_file back to the original content
echo "I was included!" > included_file.tex
mem

# mem didn't do anything because it already recognized the state of the
# current tex files. But the .pdf file in this directory didn't change, which is 
# wrong.


