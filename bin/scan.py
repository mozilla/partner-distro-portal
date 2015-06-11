import re
import sys
import os
import ftputil
import fnmatch
import argparse
import json
import subprocess
from distutils.version import LooseVersion, StrictVersion

# no reason to import a lot of old stuff for now
minVer = LooseVersion("38.0")

# partners well move over from ftp, we don't care about others for now
partners = ['1und1', 'aol', 'gmx', 'mail.com', 'web.de', 'yahoo', 'yandex']

# FTP path where we gather partner builds
rootDir = "/pub/mozilla.org/firefox/nightly/"

# temporary storage for files downloaded from ftp
tmpDir = os.path.join(os.curdir, "tmp") + "/"
if not os.path.exists(tmpDir):
  subprocess.call("mkdir -p %s" % (tmpDir), shell=True)  

builds = {}

def printOut(s):
  sys.stdout.write(s)
  sys.stdout.flush()

def getPartner(d):
  for p in partners:
    if d.startswith(p):
      return p, d
  return None, None

def getPartnerData(host, d, pd):
  partner, partnerDistro = getPartner(pd)
  # only walking select partners
  if not partner:
    return None, None, None
  printOut('\nw')
  recursive = host.walk(os.path.join(d, pd),topdown=True,onerror=None)
  downloads = []
  for root,dirs,files in recursive:
    if files:
      print root, files
      printOut('.')
      for name in files:
        downloads.append(os.path.join(root, name))
  return partner, partnerDistro, downloads

# we are purposely going to grab only the latest version for each major release
def getRepackCandidates(host):
  repackDirs = []
  candidates = []
  if args.version:
    candidates.append(os.path.join(rootDir, args.version+'-candidates'))
  else:
    printOut('l')
    names = host.listdir(rootDir)
    printOut('.')
    dirs = fnmatch.filter(names, '*-candidates')
    preCandidate = {}
    for d in dirs:
      candidate = os.path.join(rootDir, d)
      m = re.search('/(((\d+)\.[\d\.]+)(\w[\d\w]+)?)-candidates', candidate)
      print "0: ",m.groups()
      vstring = m.group(1)
      version = m.group(2)
      major = m.group(3)
      extra = m.group(4)
      print "  0: ",version, major
      lv = LooseVersion(version)
      if lv < minVer:
        print "Version too low ", vstring
        continue
      if major in preCandidate:
        # print preCandidate[major]
        if lv < preCandidate[major]['version']:
          print "Version %s lower than %s " % (vstring, preCandidate[major]['vstring'])
          continue
        elif lv == preCandidate[major]['version'] and \
          not preCandidate[major]['groups'][3] or extra < preCandidate[major]['groups'][3]:
          print "Version %s lower than %s " % (vstring, preCandidate[major]['vstring'])
          continue
          
      preCandidate[major] = {
        'groups': m.groups(),
        'vstring': vstring,
        'version': lv,
        'candidate': candidate
      }
    for version in preCandidate:
      printOut("v:%s" % preCandidate[version]['vstring'])
      candidates.append(preCandidate[version]['candidate'])
  print candidates

  # print candidates
  for candidate in candidates:
    # print candidate
    printOut('l.')
    builds = host.listdir(candidate)
    printOut('.')
    lastBuild = None
    for build in builds:
      if build > lastBuild:
        lastBuild = build

    # print os.path.join(candidate, build)
    buildDir = os.path.join(candidate, lastBuild)
    printOut(lastBuild)
    dirs = host.listdir(buildDir)
    printOut('.')
    packDirs = dirs = fnmatch.filter(dirs, 'partner-repacks*')
    # print packDirs
    for packDir in packDirs:
      repackDirs.append(os.path.join(buildDir, packDir))
  print repackDirs
  return repackDirs

def ftpGather():
  print "logging into FTP"
  with ftputil.FTPHost('ftp.mozilla.org', 'anonymous', '') as host:
      print 'logged into FTP'
  
      print "Scan for Candidates"
      for d in getRepackCandidates(host):
        m = re.search('/([\d\.\w]+)-candidates/build(\d+)/', d)
        # only grab the latest build
        version = m.group(1)
        build = m.group(2)
        if version not in builds or builds[version]["build"] < build:
          builds[version] = {
            "path": d,
            "version": version,
            "build": build,
            "partners": {}
          }

      print ""
      print "Gather download URLs"
      for version, data in builds.iteritems():
        printOut('v-%s-build%s.' % (version, data['build']))
        printOut('l')
        partnerDirs = host.listdir(data['path'])
        printOut('.')
        for pd in partnerDirs:
          partner, distro, downloads = getPartnerData(host, data['path'], pd)
          if partner:
            printOut('p-%s-d-%s-n-%s.' % (partner, distro, len(downloads)))
            if partner not in builds[version]['partners']:
              builds[version]['partners'][partner] = {}
            builds[version]['partners'][partner][distro] = downloads
            # if partner in builds[version]['partners']:
            #   builds[version]['partners'][partner].extend(downloads)
            # else:
            #   builds[version]['partners'][partner][distro] = downloads
  
      # save builds to json
      with open(os.path.join(os.curdir, 'builds.json'), 'w') as fp:
        json.dump(builds, fp)
        fp.close()

  print '.DONE scanning'
  host.close()

def transferFromFTP():
  print "Transfering files from FTP to tmp directory at ", tmpDir
  with ftputil.FTPHost('ftp.mozilla.org', 'anonymous', '') as host:
    for version, data in builds.iteritems():
      printOut('%s.' % version)
      for partner, distros in data['partners'].iteritems():
        dest = os.path.join(tmpDir, partner, version)
        for distro, files in distros.iteritems():
          printOut('%s.' % (distro))
          for fpath in files:
            fname = os.path.basename(fpath)
            fdir = os.path.dirname(fpath)
            m = re.search('/partner-repacks/(.*)', fdir)
            basedir = os.path.join(dest, m.group(1))

            destFile = os.path.join(basedir, fname)
            # make a tree in our tmp dir to download to
            subprocess.call("mkdir -p %s" % (basedir), shell=True)  
            printOut('.')
            if args.test:
              # create dummy files for testing purposes
              f = open(destFile, 'w')
              f.write('test file')
              f.close()
            else:
              print "Download %s to %s" %(fpath, destFile)
              # host.download_if_newer(fpath, destFile, 'b')
              host.download(fpath, destFile)
  host.close()
  print ""
  print "FTP Transfer finished"

def moveToS3():
  print "Transfering files to S3 from ", tmpDir
  subprocess.call("s3cmd -c %s sync --skip-existing -r %s s3://%s" % (args.s3cmd, tmpDir, args.bucket), shell=True)

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--version", help="Version to download and transfer to s3")
parser.add_argument("-j", "--json", action='store_true', help="Path to existing builds json file")
parser.add_argument("-t", "--test", action='store_true', help="Don't download binaries, just touch them for testing")
parser.add_argument("--scan", action='store_true', help="Only scan ftp, do not download binaries")
parser.add_argument("-c", "--s3cmd", default="~/.s3cfg", help="s3cmd config file")
parser.add_argument("-b", "--bucket", default="partner-distro-portal", help="bucket name")
args = parser.parse_args()

# gather data for json
if args.json:
  with open(os.path.join(os.curdir, 'builds.json'), 'r') as fp:
    builds = json.load(fp)
    fp.close()
else:
  ftpGather()

if not args.scan:
  transferFromFTP()
  moveToS3()
