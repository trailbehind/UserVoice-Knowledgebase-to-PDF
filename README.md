UserVoice-Knowledgebase-to-PDF
==============================

###Run for Gaia GPS###
1) Make sure lines 43-46 are set correctly

2) run the script, to create manual.pdf:
   python uservoiceToPDF.py

3) ask Anna to upload the new file to gaiagps.com

or put manual PDFs on S3: s3cmd put manual.pdf s3://com.gaiagps.static/

###Requirements###

 * PIL (pip install pil)

A Python script that turns a UserVoice knowledgebase into a PDF.

This script has only been tested on two sites, and you have to configure it in the script itself

 * http://help.tryskipper.com/knowledgebase
 * http://help.gaiagps.com/knowledgebase
 
It's Apache-licensed, so do whatever you want with it. 

If we had more time, we'd fix it to be configurable from the command line, and to make prettier PDFs.
