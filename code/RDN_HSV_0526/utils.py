"""Training utilities for RDN."""
import torch


def calc_psnr(img1, img2, max_val=1.0):
    """Calculate PSNR between two tensors (assumes [0, max_val] range)."""
    mse = ((img1 - img2) ** 2).mean()
    if mse == 0:
        return float('inf')
    return 10. * torch.log10(max_val ** 2 / mse)


class AverageMeter(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count
