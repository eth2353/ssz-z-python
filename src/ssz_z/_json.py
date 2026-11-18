"""Shared JSON codecs for the internal native bridge."""

from msgspec.json import Decoder, Encoder

encoder = Encoder()
decoder = Decoder()
