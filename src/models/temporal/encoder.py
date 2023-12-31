import torch
import torch.nn as nn

from typing import Union
from functools import partial

from models.common.sequential import TemporalMultiInputSequential
from models.temporal.global_attention import GlobalTemporalAttention
from models.temporal.local_attention import LocalBackwardTemporalAttention, LocalForwardTemporalAttention

      
class TemporalEncoderBlock(nn.Module):
    """ Encode a temporal sequence of local and global features
    """

    def __init__(
        self,
        direction: str, # "forward", "backward", or "both" (not configured yet)
        num_heads: int,
        hidden_dim: int,
        mlp_dim: int,
        reduce: bool=False,
        dropout: float=0.0,
        norm_layer = partial(nn.LayerNorm, eps=1e-6),
        use_global: bool=True,
        need_weights: bool=False,
        average_attn_weights: bool=True,
        activation=nn.GELU
    ):
        """Initialize Temporal Encoder Block

        Args:
            num_heads (int): Number of heads for the temporal attention module
            hidden_dim (int): Hidden dimension for the temporal attention module
            mlp_dim (int): MLP dimension for the temporal attention module
            norm_layer (torch.nn.Module, optional): Layer norm after temporal attention. 
                Defaults to partial(nn.LayerNorm, eps=1e-6).
            dropout (float, optional): Dropout probability. Defaults to 0.0.
            need_weights (bool, optional): If true, return attention weights (not configured for now). 
                Defaults to False.
            reduce (bool, optional): If true, return the propagated attended values. Else return all the attented values. 
                Defaults to False.  
            directions (list): A string of direction "forward" or "backward" 
                for the temporal attention module
        """
        torch._assert(direction in ["forward", "backward"], "Invalid direction value")
        
        super().__init__()
        self.num_heads = num_heads
        self.reduce = reduce
        self.direction = direction
        self.need_weights = need_weights 
        self.local_forward_attention = LocalForwardTemporalAttention(
            num_heads=num_heads, 
            hidden_dim=hidden_dim,
            mlp_dim=mlp_dim, 
            norm_layer=norm_layer,
            reduce=reduce,
            dropout=dropout, 
            need_weights=need_weights,
            average_attn_weights=average_attn_weights,
            activation=activation
        )
        
        self.local_backward_attention = LocalBackwardTemporalAttention(
            num_heads=num_heads, 
            hidden_dim=hidden_dim,
            mlp_dim=mlp_dim, 
            norm_layer=norm_layer,
            reduce=reduce,
            dropout=dropout, 
            need_weights=need_weights,
            average_attn_weights=average_attn_weights,
            activation=activation

        )
        
        if use_global:
            self.global_attention = GlobalTemporalAttention(
                num_heads=num_heads, 
                hidden_dim=hidden_dim,
                mlp_dim=mlp_dim, 
                norm_layer=norm_layer,
                dropout=dropout, 
                need_weights=need_weights,
                average_attn_weights=average_attn_weights,
                activation=activation

            )
        
        self.use_global = use_global
                
    def forward(self, local_feat: torch.Tensor, global_feat: Union[torch.Tensor, None]=None, mask: Union[torch.Tensor, None]=None):
        """Perform forward pass

        Args:
            local_feat (torch.Tensor): A (B, Hw, Nf, E) tensor with Hw as the history 
                window, Nf as the number of local features and E as the embedding/hidden
                feature dimension.
                
            global_feat (torch.Tensor): A (B, Hw, E) tensor with Hw as the history. 
                window and E as the embedding/hidden feature dimension.

        Returns:
            local_result (torch.Tensor): A (B, Nf, E) or (B, Hw', Nf, E) tensor if reduce is False.
            global_result (torch.Tensor) A (B, Hw, E) tensor.
        """
        torch._assert(local_feat.dim() == 4, f"Expected Local Features of shape \
            (batch_size, seq_length, num_feature, hidden_dim) got {local_feat.shape}")
        
        
        ##########################################################################
        # TODO: Need to think about forward-backward or backward-forward methods
        
        if self.direction == "forward":
            local_result, local_forward_attentions  = self.local_forward_attention(local_feat, mask)
            attention_weights = local_forward_attentions
            
        elif self.direction == "backward":
            local_result, local_backward_attentions = self.local_backward_attention(local_feat, mask)
            attention_weights = local_backward_attentions

        # elif self.direction == "backward-forward":
        #     local_result = self.local_backward_attention(local_feat)
        #     local_feat = torch.cat([local_feat[:, 1:, ...], local_result.unsqueeze(1)], dim=1)
        #     local_result = self.local_forward_attention(local_feat)
        if self.use_global:
            torch._assert(
                global_feat.dim() == 3,    
                f"Expected Global Features of shape (batch_size, seq_length, hidden_dim) got {global_feat.shape}"
            )
            
            global_result, global_attentions = self.global_attention(global_feat)
            
            return local_result, global_result, [global_attentions, attention_weights]

        return local_result, [attention_weights]
        
class TemporalEncoder(nn.Module):
    """ Temporal Encoder for local and global features
    """
    
    def __init__(
        self, 
        num_heads: int, 
        hidden_dim: int,
        mlp_dim: int,
        directions: list,
        norm_layer = partial(nn.LayerNorm, eps=1e-6),
        dropout: float=0.0,
        use_global: bool=True,
        need_weights: bool=False,
        average_attn_weights: bool=True,
        activation=nn.GELU
        ) -> None:
        """Initialize Temporal Encoder

        Args:
            num_layers (int): Number of TemporalEncoderBlock
            num_heads (int): Number of heads for all TemporalEncoderBlock
            hidden_dim (int): Hidden dimension for all TemporalEncoderBlock
            mlp_dim (int): MLP dimension for all TemporalEncoderBlock
            directions (list): A list strings of direction "forward" or "backward" 
                for the temporal attention for each TemporalEncoderBlock
            norm_layer (torch.nn.Module, optional): Layer norm after attention. 
                Defaults to partial(nn.LayerNorm, eps=1e-6).
            dropout (float, optional): Dropout probability. Defaults to 0.0.
            need_weights (bool, optional): If true, return attention weights (not configured for now). 
                Defaults to False.
        """
        super().__init__()
        
        #######################################################
        # TODO: Need to implement a temporal encoder

        layers = []
        
        for i, direction in enumerate(directions):
            layers.append(
                TemporalEncoderBlock(
                    direction=direction,
                    num_heads=num_heads, 
                    hidden_dim=hidden_dim, 
                    mlp_dim=mlp_dim,
                    reduce=True if i == (len(directions) - 1) else False,
                    dropout=dropout,
                    norm_layer=norm_layer,
                    use_global=use_global,
                    need_weights=need_weights,
                    average_attn_weights=average_attn_weights,
                    activation=activation
                )
            )
        
        self.layers = TemporalMultiInputSequential(*layers)
        self.use_global = use_global
                
    def forward(self, local_feat: torch.Tensor, global_feat: Union[torch.Tensor, None]=None, mask: Union[torch.Tensor, None]=None):
        """Perform forward pass

        Args:
            local_feat (torch.Tensor): A (B, Hw, Nf, E) tensor with Hw as the history 
                window, Nf as the number of local features and E as the embedding/hidden
                feature dimension.
                
            global_feat (torch.Tensor): A (B, Hw, E) tensor with Hw as the history 
                window and E as the embedding/hidden feature dimension.

        Returns:
            local_result (torch.Tensor): A (B, Nf, E) tensor.
            global_result (torch.Tensor) A (B, Hw, E) tensor.
        """
        torch._assert(local_feat.dim() == 4, f"Expected Local Features of shape \
            (batch_size, seq_length, num_feature, hidden_dim) got {local_feat.shape}")


        if self.use_global:
            torch._assert(global_feat.dim() == 3, f"Expected Global Features of shape \
            (batch_size, seq_length, hidden_dim) got {global_feat.shape}")
            return self.layers(local_feat, global_feat, mask=mask)
        
        else:
            return self.layers(local_feat, mask=mask)

        