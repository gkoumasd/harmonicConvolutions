'''Face loader'''

import os
import sys
import time

import numpy as np
import tensorflow as tf


def get_files(folder):
	fnames = []
	for root, dirs, files in os.walk('{:s}/addresses'.format(folder)):
		for f in files:
			if 'addresses' in f:
				fname = root + '/' + f
				fnames.append(fname)
	return fnames


def deg2rad(x):
	"""Convert degrees to radians"""
	return np.pi * x / 180.


def string2params(string1, string2):
	"""Convert the input string to 2 3D rotation matrices"""
	params1 = deg2rad(tf.string_to_number(string1))
	params2 = deg2rad(tf.string_to_number(string2.values))
	return (rot3d_a2b(params1[0], params1[1], params2[0], params2[1]),
			  rot3d_a2b(params1[2], params1[3], params2[2], params2[3]))


def string2d_params(string1, string2):
	"""Convert the input string to 2 differences in parameters"""
	params1 = deg2rad(tf.string_to_number(string1))
	params2 = deg2rad(tf.string_to_number(string2.values))
	return params2 - params1


def read_my_file_format(filename_queue, im_size, opt):
	with tf.name_scope('Read_files'):
		# Text file reader
		reader = tf.TextLineReader()
		key, value = reader.read(filename_queue)
		record_defaults = [[""],[""],[""],[""],[""]]
		address, az, el, az_light, el_light = tf.decode_csv(value, record_defaults=record_defaults)
		# Get random paired image
		split_address = tf.string_split([address], delimiter='/')
		# Generate random pairing
		paired_id = tf.as_string(tf.to_int32(tf.random_uniform([]) * 240), width=3, fill="0")
		# Stitch new address together
		paired_address = '/' + tf.reduce_join(split_address.values[0:6], 0, separator='/')
		paired_address = paired_address + '/face_' + paired_id+ '.png'
		paired_params_address = '/' + tf.reduce_join(split_address.values[0:4], 0, separator='/') \
				+ '/params/' + split_address.values[5] + '/face_' + paired_id + '.txt'
		
	# Image reader
	with tf.name_scope('Load_data'):
		# Load primary image
		file_contents1 = tf.read_file(address)
		img1 = tf.image.decode_png(file_contents1, channels=3)
		img1 = tf.to_float(img1)
		# Load transformed pair
		file_contents2 = tf.read_file(paired_address)
		img2 = tf.image.decode_png(file_contents2, channels=3)
		img2 = tf.to_float(img2)
		# Load paired params
		paired_params = tf.read_file(paired_params_address)
		split_params = tf.string_split([paired_params], delimiter=',')
		
		geometry, lighting = string2params([az,el,az_light,el_light],split_params)
		d_params = string2d_params([az,el,az_light,el_light],split_params)
	
	if opt['color'] == 1:
		img1 = tf.image.rgb_to_grayscale(img1)
		img2 = tf.image.rgb_to_grayscale(img2)
	
	img1 = tf.image.resize_images(img1, opt['im_size'], method=tf.image.ResizeMethod.AREA)
	img2 = tf.image.resize_images(img2, opt['im_size'], method=tf.image.ResizeMethod.AREA)
	img1.set_shape([opt['im_size'][0],opt['im_size'][1],opt['color']])
	img2.set_shape([opt['im_size'][0],opt['im_size'][1],opt['color']])
	
	id_ = tf.string_split([split_address.values[5]], delimiter='face').values[0]
			
	return img1, img2, geometry, lighting, d_params, id_


def get_batches(files, shuffle, opt, min_after_dequeue=1000, num_epochs=None):
	batch_size = opt['mb_size']
	im_size = opt['im_size']
	
	with tf.name_scope('Queue_runners'):
		filename_queue = tf.train.string_input_producer(files, shuffle=shuffle,
																		num_epochs=num_epochs)
		img1, img2, geometry, lighting, d_params, paired_id = read_my_file_format(filename_queue, im_size, opt)
		
		num_threads = 4
		capacity = min_after_dequeue + (num_threads+1)*batch_size
		
		img1_batch, img2_batch, geometry_batch, lighting_batch, d_params_batch, paired_id_batch = tf.train.shuffle_batch_join(
			[[img1, img2, geometry, lighting, d_params, paired_id]], batch_size=batch_size,
			capacity=capacity, min_after_dequeue=min_after_dequeue)
		
	return img1_batch, img2_batch, geometry_batch, lighting_batch, d_params_batch, paired_id_batch


def rot3d(phi, theta):
	"""Compute the 3D rotation matrix for a roll-less transformation"""
	rotY = [[tf.cos(phi),0.,-tf.sin(phi)],
				[0.,1.,0.],
				[tf.sin(phi),0.,tf.cos(phi)]]
	rotZ = [[tf.cos(theta),tf.sin(theta),0.],
				[-tf.sin(theta),tf.cos(theta),0.],
				[0.,0.,1]]
	return tf.matmul(rotZ, rotY)


def rot3d_a2b(phi1, theta1, phi2, theta2):
	"""Compute the 3D rotation matrix for a roll-less transformation from A to B"""
	rot1_inv = tf.transpose(rot3d(phi1, theta1))
	rot2 = rot3d(phi2, theta2)
	return tf.matmul(rot2, rot1_inv)


if __name__ == '__main__':
	opt = {}
	opt['color'] = 3
	opt['mb_size'] = 100
	opt['im_size'] = (150,150)
	
	data_folder = '/home/dworrall/Data/faces15'
	train_files = get_files(data_folder)
	img1, img2, geometry, lighting, d_params, ids = get_batches(train_files, True, opt)
	
	with tf.Session() as sess:
		# Threading and queueing
		coord = tf.train.Coordinator()
		threads = tf.train.start_queue_runners(coord=coord)
		try:
			while not coord.should_stop():
				Ids = sess.run([ids])
				print Ids
		finally:
			# When done, ask the threads to stop.
			coord.request_stop()
			coord.join(threads)






































