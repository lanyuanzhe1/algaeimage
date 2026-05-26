"""Train RDN for HSV polarization reconstruction.

Usage:
    python train.py --train-file data/train.h5 --eval-file data/eval.h5 \\
                    --outputs-dir checkpoint --num-epochs 100
"""
import argparse
import os
import copy
import math

import torch
from torch import nn
import torch.optim as optim
import torch.backends.cudnn as cudnn
from torch.utils.data.dataloader import DataLoader
from tqdm import tqdm

from models import RDN
from datasets import TrainDataset, EvalDataset
from utils import AverageMeter, calc_psnr


class CombinedLoss(nn.Module):
    """L1 loss + optional AoP consistency loss for polarization channels."""

    def __init__(self, l1_weight=1.0, aop_weight=0.1):
        super(CombinedLoss, self).__init__()
        self.l1_loss = nn.L1Loss()
        self.l1_weight = l1_weight
        self.aop_weight = aop_weight

    @staticmethod
    def calculate_aop(img):
        """Calculate AoP from 4-channel polarization image.
        Channels: 0=I0, 1=I45, 2=I90, 3=I135
        """
        img0 = img[:, 0:1, :, :]
        img90 = img[:, 2:3, :, :]
        img135 = img[:, 3:4, :, :]

        S1 = img0 - img90
        S2 = img0 + img90 - img135 * 2
        AoP = 0.5 * torch.atan2(S2, S1)
        AoP = (AoP + math.pi / 2) / math.pi
        return AoP

    def forward(self, pred, target):
        l1_loss = self.l1_loss(pred, target)
        pred_aop = self.calculate_aop(pred)
        target_aop = self.calculate_aop(target)
        aop_loss = self.l1_loss(pred_aop, target_aop)
        total_loss = self.l1_weight * l1_loss + self.aop_weight * aop_loss
        return total_loss, l1_loss, aop_loss


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--train-file', type=str, default='data/train.h5')
    parser.add_argument('--eval-file', type=str, default='data/eval.h5')
    parser.add_argument('--outputs-dir', type=str, default='checkpoint')
    parser.add_argument('--num-features', type=int, default=16)
    parser.add_argument('--growth-rate', type=int, default=16)
    parser.add_argument('--num-blocks', type=int, default=12)
    parser.add_argument('--num-layers', type=int, default=6)
    parser.add_argument('--lr', type=float, default=1e-4)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--num-epochs', type=int, default=100)
    parser.add_argument('--num-workers', type=int, default=0)
    parser.add_argument('--seed', type=int, default=123)
    parser.add_argument('--l1-weight', type=float, default=1.0)
    parser.add_argument('--aop-weight', type=float, default=0.1)
    args = parser.parse_args()

    if not os.path.exists(args.outputs_dir):
        os.makedirs(args.outputs_dir)

    cudnn.benchmark = True
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    torch.manual_seed(args.seed)

    model = RDN(
        num_channels=4,
        num_features=args.num_features,
        growth_rate=args.growth_rate,
        num_blocks=args.num_blocks,
        num_layers=args.num_layers,
    ).to(device)

    print(f"RDN params: {sum(p.numel() for p in model.parameters()):,}")

    criterion = CombinedLoss(l1_weight=args.l1_weight, aop_weight=args.aop_weight)
    optimizer = optim.Adam(model.parameters(), lr=args.lr)

    train_dataset = TrainDataset(args.train_file)
    train_dataloader = DataLoader(
        dataset=train_dataset, batch_size=args.batch_size,
        shuffle=True, num_workers=args.num_workers, pin_memory=True,
    )
    eval_dataset = EvalDataset(args.eval_file)
    eval_dataloader = DataLoader(dataset=eval_dataset, batch_size=1)

    best_weights = copy.deepcopy(model.state_dict())
    best_epoch = 0
    best_psnr = 0.0

    for epoch in range(args.num_epochs):
        # LR schedule: ×0.1 at 80% of training
        for param_group in optimizer.param_groups:
            param_group['lr'] = args.lr * (0.1 ** (epoch // int(args.num_epochs * 0.8)))

        model.train()
        epoch_losses = AverageMeter()
        epoch_l1_losses = AverageMeter()
        epoch_aop_losses = AverageMeter()

        with tqdm(total=len(train_dataset) - len(train_dataset) % args.batch_size,
                  ncols=120) as t:
            t.set_description(f'epoch: {epoch}/{args.num_epochs - 1}')

            for data in train_dataloader:
                inputs, labels = data
                inputs = inputs.to(device)
                labels = labels.to(device)

                preds = model(inputs)
                total_loss, l1_loss, aop_loss = criterion(preds, labels)

                epoch_losses.update(total_loss.item(), len(inputs))
                epoch_l1_losses.update(l1_loss.item(), len(inputs))
                epoch_aop_losses.update(aop_loss.item(), len(inputs))

                optimizer.zero_grad()
                total_loss.backward()
                optimizer.step()

                t.set_postfix(
                    loss=f'{epoch_losses.avg:.6f}',
                    l1=f'{epoch_l1_losses.avg:.6f}',
                    aop=f'{epoch_aop_losses.avg:.6f}',
                )
                t.update(len(inputs))

        # Checkpoint every 10 epochs
        if (epoch + 1) % 10 == 0:
            torch.save(model.state_dict(),
                       os.path.join(args.outputs_dir, f'epoch_{epoch}.pth'))

        # Evaluation
        model.eval()
        epoch_psnr = AverageMeter()

        for data in eval_dataloader:
            inputs, labels = data
            inputs = inputs.to(device)
            labels = labels.to(device)

            with torch.no_grad():
                preds = model(inputs)

            epoch_psnr.update(calc_psnr(preds, labels, max_val=1.0), len(inputs))

        print(f'eval psnr: {epoch_psnr.avg:.2f} dB')

        if epoch_psnr.avg > best_psnr:
            best_epoch = epoch
            best_psnr = epoch_psnr.avg
            best_weights = copy.deepcopy(model.state_dict())

    print(f'best epoch: {best_epoch}, psnr: {best_psnr:.2f} dB')
    torch.save(best_weights, os.path.join(args.outputs_dir, 'best.pth'))
    print(f'Saved best.pth to {args.outputs_dir}/best.pth')
