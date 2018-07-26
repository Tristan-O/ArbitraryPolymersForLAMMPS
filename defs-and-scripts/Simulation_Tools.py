# This file provides the definition of the class "event", which is a class that allows one to store various
# parameters of simulations and then simulate under those conditions
# It also contains an algorithm that serves as an example usage, 
import matplotlib.pyplot as plt
import numpy as np
import scipy.optimize as opt
import os
import math
import matplotlib
matplotlib.rcParams.update({'errorbar.capsize': 8}) #makes endcaps of errorbars visible
from matplotlib.ticker import (MultipleLocator, FormatStrFormatter, AutoMinorLocator)
import sys
import time
import subprocess as prcs
sys.path.insert(0, '../../defs-and-scripts')

def make_dat_file(Lx, Ly, Lz, n_p, n_s, N=None, N1=None, N2=None, NArms=None, Rc=0, style=None):
	'''Makes a dat file called polymer0.dat with the parameters that are necessary'''
	style = style.lower()
	if style == 'beadspring':
		if N == None:
			print 'Style beadspring requires argument N'
			sys.exit()
		import BeadSpringInit as init
		init.AtomArange(Lx, Ly, Lz, n_p, N, n_s, Rc)

	elif style == 'diblock':
		if N1 == None or N2 == None:
			print 'Style diblock requires arguments N1, N2 (which do not include endcaps)'
			sys.exit()
		import DiblockInit as init
		init.AtomArange(Lx, Ly, Lz, n_p, N1, N2, n_s, Rc)

	elif style == 'star':
		print 'Style not yet implemented'
		sys.exit()
	elif style == 'spine':
		print 'Style not yet implemented'
		sys.exit()
	else:
		print 'Invalid Style: ', style
		sys.exit()

	return


def cleanLog(infileloc, outfileloc, header='Steps Temp KinE PotE TotE Press Vol'):
	'''Cleans the log so that it can be put into stats.py, header must have same number of columns'''
	#Look for 10 lines that are just numbers
	import re # regex module

	with open(infileloc, 'r') as f:
			simulate_str = f.read()

	prog = re.compile("^[0-9. ]+$", re.MULTILINE) # match regex thermo output lines 
	result = prog.findall(simulate_str) # (might be imperfect but probably fine, can fix if it starts incorrectly matching)

	#write in csv file format if the user specifies .csv
	if outfileloc[-4:-1] == '.csv':
		delim = ','
	else:
		delim = ' '

	with open(outfileloc, "wb") as f:
		f.write('# ' + header + '\n')
		f.writelines("%s\n" % re.sub("\s+", delim, res.strip()) for res in result)
	
	for i in range(len(result)):
		result[i] = result[i].split()

	return np.array(result, float)


def do_stats(params_list, infileloc, outfileloc=None):
	'''Calls stats.py and obtains mean and error on each quantity obtained from lammps simulation, returns list of mean and std dev'''
	if type(params_list) == type(' '):
		params_list = params_list.split()

	print 'May get "divide error". This is probably from trying to do stats on volume,\nwhich is always constant and thus has an uncertainty of 0.'
	stats_data = []
	for param_i in params_list:
		print 'Doing stats on ' + str(param_i)
		tmp_str = prcs.check_output("python ../../defs-and-scripts/stats.py -o %s -f %s"  % (param_i, infileloc))
		for x in tmp_str.split('\n'): #go line by line in the output of stats.py
			if 'Mean' in x: #take third entry in line containing 'Mean' to be mean
				# Make stats_data a list of lists
				# Each sublist is len 3 and has the parameter string, mean and std dev
				stats_data.append([param_i, float(x.split()[3]), float(x.split()[5])]) #split[4] is '+/-'	

	if outfileloc != None:
		with open(outfileloc, 'wb') as f:
			f.writelines("%s\n" % stat for stat in stats_data)

	return stats_data


def plot_params(outfile, data, stats_data, numcols=None, numrows=None, t_lo=None, t_hi=None, txt = ''):
	'''Makes several plots vs time of all of the params output by lammps
	This is written to exclude the plot of timestep vs. timestep, assumed
	to be the first column of the data list.
	- The list \'data\' is assumed to be in the same format as that of the 
	output of the cleanLog() function
	- stats_data can be either the output of do_stats(), a list of the parameters
	in string format, or one string of the parameters separated by spaces'''

	if type(stats_data) == type(''):
		stats_data = stats_data.split()
	elif type(stats_data[0]) == type([]):
		temp = []
		for i in stats_data:
			temp.append(i[0][:]) # [:] - pass by value
		stats_data = temp

	if t_lo != None and t_hi != None:
		if t_lo > t_hi:
			print "Error: t_lo > t_hi"
			return

	data = data[:] #so that changes to data in this function do not affect the original argument
	# Only plot in range t_lo to t_hi
	# This is not the best way, it is just deleting every row whose 0th value is greater(less) than t_hi(t_lo)
	if t_hi != None:
		i = len(data)-1
		while i > 0: # timestep column
			if data[i][0] < t_hi:
				# as soon as this hits a step that is less than t_hi
				data = data[0:i]
				break
			i -= 1

	if t_lo != None:
		i = 0
		while i < len(data): # timestep column
			if data[i][0] > t_lo:
				# delete row
				data = data[i:len(data)]
				break
			i += 1

	if numcols == None:
		numcols = int(math.ceil(math.sqrt(len(data[0]))))
	if numrows == None:
		numrows = numcols -1

	fig = plt.figure(figsize=(25, 15))
	for i in range(1, len(data[0])):
		plt.subplot(int('%i%i%i' % (numrows, numcols, i)))
		plt.plot(data[:,0], data[:,i])
		fontsize = 18
		plt.title('%s vs Time' % stats_data[i], fontsize=fontsize)
		plt.ylabel(stats_data[i], fontsize=fontsize)
		plt.xlabel('Timestep', fontsize= fontsize)

		ax = plt.gca()

		# For the minor ticks
		ax.xaxis.set_minor_locator(AutoMinorLocator())
		ax.yaxis.set_minor_locator(AutoMinorLocator())
		ax.tick_params(which='both', width=1)
		ax.tick_params(which='major', length=10)
		ax.tick_params(which='minor', length=6)


	if txt == '':
		txt = outfile
	fig.text(0.5, 0.05, txt, ha='center', fontsize=fontsize)
	fig.savefig(outfile)#, bbox_inches='tight')

def analyzeDump(infile, style='beadspring', POLY_END_TYPE = 1, POLY_MID_TYPES = [2], COLLOID_TYPE = 4, TYPE_IGNORES = [3]):
	'''Analyze an atom-type dump file
	INPUT:
		infile: The name of an atom-type dump file generated by LAMMPS
		style: 'polymer' or 'colloid', style of the contents of the dump file
		POLY_END_TYPE and POLY_MID_TYPES: only used if style is 'polymer',
			these are the respective types of the atoms that make up the polymer.
			POLY_MID_TYPES supports multiple types in list form.'''
	if type(POLY_MID_TYPES) == int:
		POLY_MID_TYPES = [POLY_MID_TYPES]
	if POLY_END_TYPE in POLY_MID_TYPES:
		print 'ERROR: You specified that the end type of the polymer was in POLY_MID_TYPES.'
		raise ValueError
	if type(TYPE_IGNORES) == int:
		TYPE_IGNORES = [TYPE_IGNORES]

	# Create a class of atoms so that I can 
	class Atom:
		def __init__(self, id_, type_):
			# the _ is there because id and type are built in to python and can't be overridden
			self.Pos = []
			self.Box = []
			self.neighList = []
			self.atomType = int(type_)
			self.atomID = int(id_)

		def addCoord(self, pos, box):
			'''Add a coordinate to this atom
			The expected box is of the form [(xlo,xhi),(ylo,yhi),(zlo,zhi)]'''
			for i in range(3):
				pos[i] = float(pos[i])
				for j in range(2):
					box[i][j] = float(box[i][j])	
			self.Pos.append(pos)
			self.Box.append(box)

		def addNeighbor(self, neighbor):
			'''Specify an atom that is bonded to this one'''
			self.neighList.append(neighbor)


	#First must generate a list of atoms with their respective IDs and atom types
	print 'Creating atom list'
	with open(infile, 'rb') as f:
		dumplist = f.read().split('ITEM: TIMESTEP')

	atoms = []
	del dumplist[0] # this is an empty string
	for i in dumplist[0].split('ITEM: ATOMS id type xs ys zs')[1].split('\n'): 
	# This is a terrible way of looping through the lines that have the initial position info I need
		#print repr(i)
		if i == '':
			continue
		line = i.split()
		id_ = line[0]
		type_ = line[1]
		atoms.append(Atom(id_, type_))
	atoms.sort(key=lambda atom: atom.atomID) #Sort atoms by ID


	#Fill atoms with position data
	print 'Filling position values'
	for timestepData in dumplist:
		temp = timestepData.split('ITEM: ATOMS id type xs ys zs')[1].split('\n')
		temp2 = timestepData.split('ITEM: ATOMS id type xs ys zs')[0].split('ITEM: BOX BOUNDS pp pp pp')[1].split('\n')
		box = []
		for i in temp2:
			if i != '':
				box.append(i.split())		

		for atom_data in temp:
			# print repr(atom_data)
			if atom_data == '':
				continue
			atom_data = atom_data.split()
			id_ = int(atom_data[0]) # id
			Pos = [float(atom_data[2]), float(atom_data[3]), float(atom_data[4])]

			if atoms[id_-1].atomID == id_: #because atoms list was sorted earlier, I can do this
				atoms[id_-1].addCoord(Pos, box)
			else:
				print "ID not found ", id_
				print timestepData.split('ITEM: ATOMS id type xs ys zs')[0]
				raise ValueError


	#list of atoms has been filled with ID, type and position data
	#Now to add neighbors
	print 'Adding neighbors'
	if style == 'beadspring':

		polyEnd = False
		for i in range(len(atoms)):
			if atoms[i].atomType == POLY_END_TYPE:
				if not polyEnd:
				# This atom is on the end of a polymer, and it is the beginning of a polymer
					atoms[i].addNeighbor(atoms[i+1])
					polyEnd = True
				else:
					atoms[i].addNeighbor(atoms[i-1])
					polyEnd = False
			elif atoms[i].atomType in POLY_MID_TYPES:
				atoms[i].addNeighbor(atoms[i+1])
				atoms[i].addNeighbor(atoms[i-1])
			elif atoms[i].atomType not in TYPE_IGNORES:
				print "WARNING: Atom of unknown type encountered."
				print "atom ID ", atoms[i].atomID
	elif style == 'colloid':
		colloids = []
		for i in range(len(atoms)):
			if atoms[i].atomType != COLLOID_TYPE and atoms[i].atomType not in TYPE_IGNORES:
				print "WARNING: Atom of unknown type encountered."
				print "Atom ID ", atoms[i].atomID
			else:
				colloids.append(atoms[i])
		for i in colloids:
			for j in colloids:
				colloids[i].addNeighbor(colloids[j])
		atoms = colloids[:]


	print 'Calculating distance data of neighbors'
	#generate distance data of neighbors
	allNeighbors = []
	for i in atoms:
		for j in i.neighList:
			if i.atomID < j.atomID: #I do this so that the first element of the tuple is always less than the second, so that I can remove clones later
					  # because (1,2) != (2,1)
				neighs = (i.atomID, j.atomID)
			else:
				neighs = (j.atomID, i.atomID)
			# timesteps = len(i.Pos)
			for k in range(len(i.Pos)):
				#Find minimum distance - because periodic boundaries are a thing the bond might be across two walls
				dist = math.sqrt(sum(min( (i.Pos[k][l]-j.Pos[k][l])**2. , (i.Pos[k][l]-i.Box[k][l][0]-j.Pos[k][l]+j.Box[k][l][1])**2., (-i.Pos[k][l]+i.Box[k][l][1]+j.Pos[k][l]-j.Box[k][l][0])**2. ) for l in range(3)))
				# Pretty sure the above formula is right, it's the distance between atom1 and the wall + the distance between atom2 and the opposite wall
				# if dist > 0.5 and i.atomID == 19 and j.atomID == 20:
				# 	print dist
				# 	for l in range(3):
				# 		print (i.Pos[k][l]-j.Pos[k][l]), (i.Pos[k][l]-i.Box[k][l][0]-j.Pos[k][l]+j.Box[k][l][1]), (-i.Pos[k][l]+i.Box[k][l][1]+j.Pos[k][l]-j.Box[k][l][0])
			allNeighbors.append([neighs,dist])

	temp = []
	for neigh in allNeighbors:
		if neigh not in temp:
			temp.append(neigh)
	allNeighbors = temp

	#Finally, generate some histograms
	#I think I want all distances involved, as well as some individual bond distances vs. time although unless the timesteps are small for this, they are going to be useless
	print 'Generating plots'
	dists = []
	for i in allNeighbors:
		dists.append(i[1])
		# if i[1] > 0.5:
		# 	print i
	plt.hist(dists, 200)
	plt.show()
	plt.hist(dists, 1000)
	plt.xlim(0,0.2)
	plt.show()


# if __name__ == "__main__":
# 	#simulate_str = prcs.check_output("../../defs-and-scripts/lmp_serial -sf omp -pk omp 4 -in polymer.in")