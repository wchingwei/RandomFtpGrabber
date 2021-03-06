# MusicPlayer, https://github.com/albertz/music-player
# Copyright (c) 2012, Albert Zeyer, www.az2000.de
# All rights reserved.
# This code is under the 2-clause BSD license, see License.txt in the root directory of this project.

# loosely inspired from https://github.com/albertz/PictureSlider/blob/master/PictureSlider/FileQueue.cpp

import random
import sys
import FileSysIntf

kNonloadedDirsExpectedFac = 0.5
kNonloadedDirsExpectedMin = 100

rndInt = random.randint


class RandomFileQueue:
	def __init__(self, rootdir, filesystem):
		self.rootdir = rootdir
		self.fs = filesystem

		class Dir:
			owner = self
			isLoaded = False
			base = None

			def __init__(self):
				self.files = []
				self.loadedDirs = []
				self.nonloadedDirs = []

			def load(self):
				self.isLoaded = True
				# Note: If we could use the C readdir() more directly, that would be much faster because it already provides the stat info (wether it is a file or dir), so we don't need to do a separate call for isfile/isdir.
				try:
					listeddir = self.owner.fs.listDir(self.base)
				except self.owner.fs.TemporaryException:
					# try again another time
					self.isLoaded = False
					raise # fall down to bottom
				except Exception:
					self.owner.fs.handleException(*sys.exc_info())
					# it might fail because of permission errors or whatever
					listeddir = []
				for f in listeddir:
					if self.owner.fs.isFile(f):
						self.files += [f]
					elif self.owner.fs.isDir(f):
						subdir = Dir()
						subdir.base = f
						self.nonloadedDirs += [subdir]

			def expectedFilesCount(self):
				c = 0
				c += len(self.files)
				for d in self.loadedDirs:
					c += d.expectedFilesCount()
				c += len(self.nonloadedDirs) * \
					max(int(kNonloadedDirsExpectedFac * c), kNonloadedDirsExpectedMin)
				return c
				
			def randomGet(self):
				if not self.isLoaded: self.load()
				if not self.isLoaded: return None

				while True:
					rmax = self.expectedFilesCount()
					if rmax == 0: return None
					r = rndInt(0, rmax - 1)
					
					if r < len(self.files):
						return self.files[r]
					r -= len(self.files)
					
					for d in self.loadedDirs:
						c = d.expectedFilesCount()
						if r < c:
							f = d.randomGet()
							if f: return f
							r = None
							break
						r -= c
					if r is None: continue
					
					assert len(self.nonloadedDirs) > 0
					r = rndInt(0, len(self.nonloadedDirs) - 1)
					d = self.nonloadedDirs[r]
					self.nonloadedDirs = self.nonloadedDirs[:r] + self.nonloadedDirs[r+1:]
					d.load()
					self.loadedDirs += [d]
					
		self.root = Dir()
		self.root.base = rootdir
		
	def getNextFile(self):
		return self.root.randomGet()
