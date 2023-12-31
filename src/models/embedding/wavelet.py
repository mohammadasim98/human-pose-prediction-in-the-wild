#####################################################
# TODO: If possible implement Wavelet based encoding
#####################################################

import base_encoding
import torch
import torch.nn as nn

class WaveEncoding(base_encoding.BaseEncoding):
    """Applies positional encoding with absolut positional values"""

    def __int__(self,
                batch_size: int,
                seq_length: int,
                d_model: int,
                n: int = 10000):
        super().__init__(batch_size, seq_length, d_model, n)
        self.encoding_matrix = self.build_encoding_matrix()

    def build_encoding_matrix(self):
        raise NotImplementedError

    def forward(self, input: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError
