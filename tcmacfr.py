# -*- coding: utf-8 -*-
"""TCMACFR.ipynb

Automatically generated by Colaboratory.

Original file is located at
	https://colab.research.google.com/drive/1hD5Cb9M9bkOza27sNHbgkCj72SqLhlaU

# Trying to do facial recognition with transformers and convolutional layers. 

Diagram: 

(Encoder * n)
->
(Convolutional Layer(s))
-> 
(Convolutional Transposing Layer(s))
"""

import tensorflow_datasets as tfds
import tensorflow_addons as tfa
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
import os
import PIL
import PIL.Image

from time import sleep

"""Do dataset stuff"""

image_height = 128
image_width = 128

dataset = tf.keras.utils.image_dataset_from_directory(
	"rsfds_large/",
	labels=None,
	label_mode=None,
	seed=123,
	image_size=(image_height, image_width),
	batch_size=256,
	validation_split=0.2,
	subset="training",
)
validation_dataset = tf.keras.utils.image_dataset_from_directory(
	"rsfds_large/",
	labels=None,
	label_mode=None,
	seed=123,
	image_size=(image_height, image_width),
	batch_size=256,
	validation_split=0.2,
	subset="validation"
)

ra_dataset = tf.keras.utils.image_dataset_from_directory(
	"rsfds_small/",
	labels=None,
	label_mode=None,
	seed=123,
	image_size=(image_height, image_width),
	batch_size=256,
	validation_split=0.2,
	subset="training",
)

print("[TCMAC] - LOADED DATA")

def format_data(data):

	reformatted = (data / 255.0)
	return reformatted, reformatted

ra_dataset.map(format_data)
ra_dataset = list(ra_dataset)[:100]
dataset = dataset.map(format_data)
validation_dataset = validation_dataset.map(format_data)

print("[TCMAC] - DATA FORMATTED")

"""**Define layers**

Convolutional layers
"""

class Compression(tf.keras.layers.Layer):
	def __init__(self, **kwargs):
		super().__init__()
		
		self.seq = tf.keras.Sequential([
			tf.keras.layers.Conv2D(20, 5, use_bias=True, strides=2, padding="same", activation="leaky_relu", input_shape=(image_height, image_width, 3)),
			tf.keras.layers.Conv2D(50, 5, use_bias=True, strides=2, padding="same", activation="leaky_relu"),
			tf.keras.layers.Conv2D(50, 5, use_bias=True, strides=2, padding="same", activation="leaky_relu"),
		])

	def call(self, x):
		return self.seq(x)

class Decompression(tf.keras.layers.Layer):
	def __init__(self, **kwargs):
		super().__init__()
		
		self.seq = tf.keras.Sequential([
			tf.keras.layers.Conv2DTranspose(50, 5, use_bias=True, strides=2, padding="same", activation="leaky_relu"),
			tf.keras.layers.Conv2DTranspose(20, 5, use_bias=True, strides=2, padding="same", activation="leaky_relu"),
			tf.keras.layers.Conv2DTranspose(3, 5, use_bias=True, strides=2, padding="same", activation="leaky_relu"),
		])

	def call(self, x):
		return self.seq(x)

"""Test the conv lay3rs out

Chunker
"""

def extract_patches(x, patch_size):
	return tf.image.extract_patches(
		x,
		(1, patch_size, patch_size, 1),
		(1, patch_size, patch_size, 1),
		(1, 1, 1, 1),
		padding="VALID"
	)

class Chunker(tf.keras.layers.Layer):

	def __init__(self, patch_size):
		super().__init__()
		self.patch_size = patch_size

	def call(self, x):
		begin_shape = tf.shape(x)[0]

		# TODO: ONLY WORKS ON 256 x 256 images
		# image_chunks = tf.image.extract_patches(images=x,
		#                    sizes=[1, self.patch_size, self.patch_size, 1],
		#                    strides=[1, self.patch_size, self.patch_size, 1],
		#                    rates=[1, 1, 1, 1],
		#                    padding='VALID')
		image_chunks = extract_patches(x, self.patch_size)
		# Reshape and flatten


		return tf.reshape(image_chunks, (begin_shape, (int(x.shape[1]) ** 2) // (self.patch_size ** 2), (self.patch_size ** 2) * 3))

@tf.function
def extract_patches_inverse(shape, patches, patch_size):
	_x = tf.zeros(shape)
	_y = extract_patches(_x, patch_size)
	grad = tf.gradients(_y, _x)[0]
	return tf.gradients(_y, _x, grad_ys=patches)[0] / grad

class Dechunker(tf.keras.layers.Layer): 
	def __init__(self, begin_size, chunked_size): 
		super().__init__() 
		self.begin_size = begin_size
		self.chunked_size = chunked_size

	def call(self, x): 
		begin_shape = tf.shape(x)[0]
		return extract_patches_inverse((begin_shape, self.begin_size, self.begin_size, 3), x, self.chunked_size)

chu = Chunker(8)
dchu = Dechunker(128, 8)

image = np.array([ra_dataset[0][1]])

plt.imshow(dchu(chu(image))[0] / 255.0)

"""Positional encoding layer"""
class PatchEncoder(tf.keras.layers.Layer):
	def __init__(self, num_patches, projection_dim):
		super().__init__()
		self.num_patches = num_patches
		self.projection = tf.keras.layers.Dense(units=projection_dim)
		self.position_embedding = tf.keras.layers.Embedding(
			input_dim=num_patches, output_dim=projection_dim
		)

	def call(self, patch):
		positions = tf.range(start=0, limit=self.num_patches, delta=1)
		encoded = self.projection(patch) + self.position_embedding(positions)
		return encoded


# def positional_encoding(length, depth):
#     depth = depth/2

#     positions = np.arange(length)[:, np.newaxis]     # (seq, 1)
#     depths = np.arange(depth)[np.newaxis, :]/depth   # (1, depth)

#     angle_rates = 1 / (10000**depths)         # (1, depth)
#     angle_rads = positions * angle_rates      # (pos, depth)

#     pos_encoding = np.concatenate(
#     [np.sin(angle_rads), np.cos(angle_rads)],
#     axis=-1) 

#     return tf.cast(pos_encoding, dtype=tf.float32)

# class PositionalEmbedding(tf.keras.layers.Layer):
#     def __init__(self, dimensions, length):
#         super().__init__()
#         self.d_model = dimensions
#         self.pos_encoding = positional_encoding(length=length, depth=dimensions)

#     def call(self, x):
#         length = tf.shape(x)[1]
		
#         # This factor sets the relative scale of the embedding and positonal_encoding.
#         x *= tf.math.sqrt(tf.cast(self.d_model, tf.float32))
#         x = x + self.pos_encoding[tf.newaxis, :length, :]
#         return x

"""Attention layers (orange): """

class BaseAttention(tf.keras.layers.Layer):
	def __init__(self, **kwargs):
		super().__init__()
		self.multihead_attn = tf.keras.layers.MultiHeadAttention(**kwargs)
		self.layernorm = tf.keras.layers.LayerNormalization()
		self.add = tf.keras.layers.Add()

class GlobalSelfAttention(BaseAttention):
	def call(self, x):
		attn_output = self.multihead_attn(
			query=x,
			value=x,
			key=x)
		x = self.add([x, attn_output])
		x = self.layernorm(x)
		return x

# image = np.array([ra_dataset[0][0]])
# chu = Chunker(8)
# pos = PositionalEmbedding(dimensions=192, length=1024)


# gsa = GlobalSelfAttention(num_heads=8, key_dim=2048, dropout = 0.1)

# chu_img = chu(image)
# pos_img = pos(chu_img)

# img = gsa(chu_img)
# print(pos_img.shape, img.shape)

"""Feed forward layer (blue):"""

class FeedForward(tf.keras.layers.Layer):
	def __init__(self, model_dim, ff_dim, dropout_rate=0.1):
		super().__init__()
		self.seq = tf.keras.Sequential([
			tf.keras.layers.Dense(ff_dim, activation='relu'),
			tf.keras.layers.Dense(model_dim),
			tf.keras.layers.Dropout(dropout_rate)
		])
		self.add = tf.keras.layers.Add()
		self.layer_norm = tf.keras.layers.LayerNormalization()

	def call(self, x):
		x = self.add([x, self.seq(x)])
		x = self.layer_norm(x) 
		return x

# sample_ffn = FeedForward(192, 2048)


# print(img.shape, sample_ffn(img).shape)

"""Define transformer encoder (decoder not requried)"""

class EncoderLayer(tf.keras.layers.Layer):
	def __init__(self,*, model_dims, num_heads, ff_dims, dropout_rate=0.1):
		super().__init__()

		self.self_attention = GlobalSelfAttention(
			num_heads=num_heads,
			key_dim=model_dims,
			dropout=dropout_rate)

		self.ffn = FeedForward(model_dims, ff_dims)

	def call(self, x):
		x = self.self_attention(x)
		x = self.ffn(x)
		return x

# sample_encoder_layer = EncoderLayer(model_dims=192, num_heads=8, ff_dims=2048)

# print(img.shape)
# print(sample_encoder_layer(img).shape)

"""# Encoder"""

class Encoder(tf.keras.layers.Layer):
	def __init__(self, *, num_layers, model_dims, num_heads, ff_dims, embedding_length, dropout_rate=0.1):
		super().__init__()

		self.model_dims = model_dims
		self.num_layers = num_layers

		self.pos_embedding = PatchEncoder(num_patches = 256, projection_dim = self.model_dims)

		self.enc_layers = [
			EncoderLayer(
				model_dims=model_dims,
				num_heads=num_heads,
				ff_dims=ff_dims,
				dropout_rate=dropout_rate
			)
			for _ in range(num_layers)]
		self.dropout = tf.keras.layers.Dropout(dropout_rate)

	def call(self, x):
		# `x` is token-IDs shape: (batch, seq_len)
		x = self.pos_embedding(x)  # Shape `(batch_size, seq_len, d_model)`.
		# Add dropout.
		x = self.dropout(x)

		for i in range(self.num_layers):
			x = self.enc_layers[i](x)

		return x  # Shape `(batch_size, seq_len, d_model)`.

sample_encoder = Encoder(
	num_layers=4,
	model_dims=192,
	num_heads=8,
	embedding_length = 4096,
	ff_dims=2048,

)

# sample_encoder_output = sample_encoder(img, training=False)

# # Print the shape.
# print(img.shape)
# print(sample_encoder_output.shape)

class FacialRecognition(tf.keras.Model): 
	def __init__(self, *, num_layers, model_dims, num_heads, ff_dims, chunk_size, input_shape, dropout_rate=0.1):
		super().__init__()

		self.encoder = tf.keras.Sequential([
			tf.keras.layers.Input((input_shape, input_shape, 3)),
			Chunker(chunk_size),
			Encoder(
				num_layers=num_layers,
				model_dims=model_dims,
				num_heads=num_heads,
				ff_dims=ff_dims,
				embedding_length = 1024,
				dropout_rate = dropout_rate
			),
			Dechunker(input_shape, chunk_size),
		])

		self.compresser = tf.keras.Sequential([
			tf.keras.layers.Flatten(),
			tf.keras.layers.Dense(1024),
			tf.keras.layers.Dense(512),
			tf.keras.layers.Dense(128),
		])
		
		self.decompresser = tf.keras.Sequential([
			tf.keras.layers.Dense(128),
			tf.keras.layers.Dense(512),
			tf.keras.layers.Dense(1024),
			tf.keras.layers.Dense(input_shape * input_shape * 3),
			tf.keras.layers.Reshape((input_shape, input_shape, 3)),
			
		])

	def call(self, x): 
		x = self.encoder(x)
		x = self.compresser(x)
		x = self.decompresser(x)
		return x

model = FacialRecognition(
	num_layers = 8, 
	model_dims = 192, 
	num_heads = 4, 
	ff_dims = 2048,
	chunk_size = 8,
	input_shape = 128
)

print(image[0].shape)
print(model.predict(np.array([image[0]])).shape)

model.compile(
    optimizer=tfa.optimizers.AdamW(
        learning_rate=0.001, weight_decay=0.0001
    ),
    loss=tf.keras.losses.MeanSquaredError(),
    metrics = ["accuracy"]
)

model.fit(
    dataset.prefetch(8),
    validation_data=(validation_dataset.cache()),
    shuffle=True,
    epochs = 10
)

model.save('my_model')
model = tf.keras.models.load_model('my_model')

predict_img = np.array([ra_dataset[0][10]]) / 255.0
test_enc = model.encoder.predict(predict_img)
test_dec = model.compresser.predict(test_enc)
test_dec = model.decompresser.predict(test_dec)

plt.imshow(test_enc[0])
plt.show()
plt.imshow(predict_img[0] )
plt.show()
sleep(20)