###############################################
# TODO: Implement positional encoding
###############################################

import torch
from torch import nn
import base_encoding
import math


class PosEncoding(base_encoding.BaseEncoding):
    """Applies positional encoding with absolut positional values"""

    def __int__(self,
                batch_size: int,
                seq_length: int,
                d_model: int,
                n: int = 10000):
        super().__init__(batch_size, seq_length, d_model, n)
        self.encoding_matrix = self.build_encoding_matrix()

    def build_encoding_matrix(self):
        encoding_matrix = torch.empty((self.batch_size, self.seq_length, self.d_model))
        for k in range(self.seq_length):
            for i in range(int(self.d_model / 2)):
                for j in range(self.batch_size):
                    encoding_matrix[j, k, 2 * i] += k / self.seq_length
                    encoding_matrix[j, k, 2 * i + 1] += k / self.seq_length
        return encoding_matrix

    def forward(self, input: torch.Tensor) -> torch.Tensor:

        return input + self.encoding_matrix
