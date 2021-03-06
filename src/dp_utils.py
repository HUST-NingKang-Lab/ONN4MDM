import os
import pickle
import numpy as np
import pandas as pd
from copy import deepcopy
from tqdm import tqdm, trange
from pandas import read_csv, DataFrame
from treelib import Node, Tree
from functools import reduce
from sklearn.ensemble import RandomForestRegressor
from copy import copy
from pprint import pprint


# Tree class for phylogenetic tree and ontology tree
class SuperTree(Tree):

	def get_bfs_nodes(self, ):
		# tested
		# Get nodes in Breadth First Traversal order.
		nodes = {}
		for i in range(self.depth()+1):
			nodes[i] = []
			for node in self.expand_tree(mode=2):
				if self.level(node) == i: 
					nodes[i].append(node)
		return nodes

	def get_bfs_data(self, ):
		# tested
		# Get nodes' data in Breadth First Traversal order.
		nodes = self.get_bfs_nodes()
		return {i: list(map(lambda x: self[x].data, nodes[i])) for i in range(self.depth() + 1)}

	def get_dfs_nodes(self, ):
		# tested
		# Get nodes in Depth First Traversal order.
		return self.paths_to_leaves()

	def get_dfs_data(self, ):
		# tested
		# Get nodes' data in Depth First Traversal order.
		paths = self.get_dfs_nodes() # list
		return [list(map(lambda x: self[x].data, path)) for path in paths]

	def init_nodes_data(self, value = 0):
		# tested
		# Initialize nodes' data into value.
		for id in self.expand_tree(mode=1):
			self[id].data = value

	def from_paths(self, paths):
		# tested
		# Construct the tree using node paths
		for path in paths:
			current_node = self.root
			for nid in path:
				children_ids = [n.identifier for n in self.children(current_node)]
				if nid not in children_ids: self.create_node(identifier=nid, parent=current_node)
				current_node = nid

	def from_pickle(self, file: str):
		# Restore the tree from a pickle dump.
		with open(file, 'rb') as f: 
			stree = pickle.load(f)
		return stree

	def path_to_node(self, node_id: str):
		# tested
		# Get path to a node
		nid = node_id
		path_r = []
		while nid != 'root':
			path_r.append(nid)
			nid = self[nid].bpointer
		path_r.append('root')
		path_r.reverse()
		return path_r
	
	def fill_with(self, data: dict):
		# tested
		for nid, val in data.items():
			self[nid].data = val

	def update_value(self, ):
		# tested
		# Recalculate abundance for all taxa from the bottom up.
		all_nodes = [nid for nid in self.expand_tree(mode=2)][::-1]
		for nid in all_nodes:
			d = sum([node.data for node in self.children(nid)])
			self[nid].data = self[nid].data + d

	def to_pickle(self, file: str):
		# tested
		# Dump the tree into pickle format.
		with open(file, 'wb') as f:
			pickle.dump(self, f)

	def get_matrix(self, dtype = np.float32):
		# tested
		# Generate the Matrix using data stored in nodes.
		paths_to_leaves = self.paths_to_leaves()
		ncol = self.depth() + 1
		nrow = len(paths_to_leaves)
		Matrix = np.zeros(ncol*nrow, dtype=dtype).reshape(nrow, ncol)

		for row, path in enumerate(paths_to_leaves):		
			for col, nid in enumerate(path):
				Matrix[row, col]= self[nid].data
		return Matrix

	def to_matrix_npy(self, file: str, dtype = np.float32):
		# tested
		# Save the Matrix into a file.
		matrix = self.get_matrix(dtype=dtype)
		np.save(file, matrix)

	def copy(self, ):
		# tested
		# Get a deep copy of the tree.
		return deepcopy(self)

	def remove_levels(self, level: int):
		# tested
		# Cut the tree, only keep nodes with levels < `level`.
		nids = list(self.expand_tree(mode=1))[::-1]
		for nid in nids:
			if self.level(nid) >= level:
				self.remove_node(nid)  # check

	def save_paths_to_csv(self, file: str, fill_na=True):
		# tested
		# Save all paths of the tree into a csv file.
		paths = self.paths_to_leaves()
		df = pd.DataFrame(paths)
		if fill_na:
			df.fillna('')
		df.to_csv(file, sep = ',')

	'''
	def from_paths_csv(self, file: str):
		# debug needed
		df = read_csv(file, header=0, sep=',')
		def remove_null_str(x): 
			while '' in x: x.remove('')
			return x
		paths = map(remove_null_str, [list(df.iloc(0)[i]) for i in df.axes[0]])
		return self.from_paths(paths)
	
	def from_ete3_species(self, name: str):
		
		# return a subtree of species name, data is retrived from NCBI Taxonomy database
		
		return None
	'''


class DataLoader(object):

	def __init__(self, path: str, ftype='.tsv', batch_size = -1, batch_index = -1):
		# tested
		self.ftype = ftype
		paths = self.get_file_paths(path, ftype)
		if batch_index is not -1 and batch_size is not -1: 
			self.paths = self.split_batches(paths, batch_size)[batch_index]
		else:
			self.paths = paths
	
	def get_file_paths(self, path: str, ftype):
		# tested
		biome_dirs = [os.path.join(path, biome) for biome in os.listdir(path)]
		tsv_dirs = [[os.path.join(biome_dir, tsv) for tsv in os.listdir(biome_dir) 
					 if tsv.endswith(ftype)] for biome_dir in biome_dirs]
		return reduce(lambda x, y: x + y, tsv_dirs)

	def split_batches(self, samples, batch_size):
		# tested
		s = batch_size
		batches = [samples[ix*s: (ix+1)*s] if (ix+1)*s < len(samples) else samples[ix*s:] 
					for ix in range(int(len(samples) / batch_size) + 1)]
		return batches

	def get_sample_count(self, ):
		self.get_paths_keep()
		split_paths = list(map(lambda x: os.path.split(x)[0].split('/')[-1], self.paths_keep))
		self.sample_count = {i: split_paths.count(i) for i in set(split_paths)}
		return self.sample_count

	def get_paths_keep(self, ):
		self.load_error_list()
		self.paths_keep = list(filter(lambda x: x not in self.error_list, self.paths))
		return self.paths_keep

	def get_data(self, header=1):
		# tested
		self.get_paths_keep()
		print('Loading data')
		self.data = [read_csv(x, sep='\t', header=header) for x in tqdm(self.paths_keep)]
		# self.data = map(lambda x: x.iloc(1)[1:], self.data)
		return self.data

	def save_error_list(self, ):
		# tested
		msg = ['{} --> {}'.format(file, err) for file, err in self.error_msg.items()]
		with open('tmp/error_msg', 'w') as f:
			f.write('\n'.join(msg))
		with open('tmp/error_list', 'w') as f:
			f.write('\n'.join(self.error_msg.keys()))
	
	def load_error_list(self, ):
		# tested
		with open('tmp/error_list', 'r') as f:
			self.error_list = [i.rstrip('\n') for i in f.readlines()]

	def check_data(self, header=1):
		# tested
		self.status = {}
		print('Checking data integrity')
		for path in tqdm(self.paths):
			try: 
				f = read_csv(path, header=header, sep='\t')
				self.status[path] = [self.check_ncols(f), self.check_sum(f),
				self.check_col_name(f), 
				self.check_values(f)]

			except:
				self.status[path] = ['IOError', 'IOError', 'IOError', 'IOError']
		self.error_msg = {path: status 
		for path, status in self.status.items() 
		if list(set(status)) != ['True']}

	def check_ncols(self, File):
		# tested
		if File.shape[1] == 3:
			return 'True'
		else:
			return 'False'
	
	def check_sum(self, File):
		cols = File.columns
		return str(File[cols[1]].sum() != 0)

	def check_col_name(self, File):
		# tested
		Colnames = File.columns.tolist()
		#print(Colnames)
		if Colnames[0] in ['# OTU ID', '#OTU ID']:
			return 'True'
		else:
			return 'False'

	def check_values(self, File):
		# tested
		Na_status = File.isna().values.any()
		Neg_status = list(set([int(ele) >=0 for ele in File[File.columns.tolist()[1]]]))
		if Na_status == True:
			return 'Na'
		elif len(Neg_status)==0 and Neg_status[0] == False:
			return 'Negtive value error'
		else:
			return 'True'


class IdConverter(object):
	def __init__(self, ):
		pass

	def fix_issue2_3(self, ids_path: str):
		ids_path = ids_path.replace('; ', ';')
		ids_path = ids_path.replace('k__', 'sk__').replace(';p__', ';k__;p__') if ids_path.startswith('k__') else ids_path
		return ids_path

	def convert(self, ids_path: str, sep):
		# tested, use path
		ids = ids_path.split(sep)
		tail = ids[-1].split('__')[-1]
		ids = list(map(lambda x: x+tail if x[-2:] == '__' else x, ids))
		ids = [sep.join(ids[0:i]) for i in range(1, len(ids)+1)]
		self.nid = ids
		return ids


class Selector(object):

	def __init__(self, matrices):
		self.matrices = matrices
		self.sum_matrix = matrices.sum(axis=0)
		self.basic_select__ = np.array([])
		self.label = np.array([])
		self.RF_select__ = np.array([])
		self.feature_importance = np.array([])
		self.is_nonZero = self.sum_matrix != 0 

	def run_basic_select(self, coefficient):
		# tested
		"""
		drop features: sum_matrix[:, i] < sum_matrix[:, i].mean() / 1000
		add threshold
		"""
		#s = self.matrices.shape
		#s_ma = self.sum_matrix
		C = coefficient
		#is_greater = np.array([s_ma[:, i] >= (s_ma[:, i].mean() * coefficient) for i in range(s[2])]).T
		is_greater = np.apply_along_axis(func1d=lambda x: x >= (C * x.mean()), axis=0, arr=self.sum_matrix)

		#self.basic_select__ = np.array([is_greater[i].sum() == self.is_nonZero[i].sum() for i in range(s[1])])
		self.basic_select__ = is_greater.sum(axis=1) == self.is_nonZero.sum(axis=1)

	def cal_feature_importance(self, label, n_jobs=10, max_depth=10):
		# tested
		"""
		"""
		shape = self.matrices.shape
		self.label = label
		importance = np.zeros(shape[1:])
		for i in trange(shape[2]):
			model = RandomForestRegressor(random_state=1, max_depth=max_depth, n_jobs=n_jobs)
			model.fit(self.matrices[:, :, i], label)
			importance[:, i] = model.feature_importances_
		self.feature_importance = importance

	def run_RF_regression_select(self, coefficient):
		# tested
		"""
		add threshold
		"""
		C = coefficient
		shape = self.matrices.shape
		importance = self.feature_importance
		'''
		is_important_T = np.array([importance[:, i] >= (importance[:, i].mean() * coefficient) for i in range(shape[2])])
		is_important = is_important_T.T
		'''
		is_important = np.apply_along_axis(func1d=lambda x: x >= (C * x.mean()), axis=0, arr=importance)

		n_nonZero = np.apply_along_axis(func1d=lambda x: x.sum(), axis=1, arr=self.is_nonZero)
		RF_select__ = [is_important[i, 0:n_nonZero[i]].sum() == n_nonZero[i] for i in range(shape[1])]
		self.RF_select__ = np.array(RF_select__)


def npz_merge(files):
	# tested
	npzs = [np.load(file) for file in files]
	keys = ['matrices', 'label_0', 'label_1', 'label_2', 'label_3', 'label_4']
	data = {key: np.concatenate([npz[key] for npz in tqdm(npzs)], axis=0) for key in keys}
	return data























