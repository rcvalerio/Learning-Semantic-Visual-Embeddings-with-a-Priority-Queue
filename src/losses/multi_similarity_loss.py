import torch
from torch import nn

class MultiSimilarityLoss(nn.Module):
    def __init__(self, scale_pos, scale_neg, margin):
        super(MultiSimilarityLoss, self).__init__()
        self.thresh = 0.5
        self.margin = margin

        self.scale_pos = scale_pos
        self.scale_neg = scale_neg
        self.hard_mining = True

    def forward(self, inputs_col, targets_col, inputs_row, target_row):
        batch_size = inputs_col.size(0)
        sim_mat = torch.matmul(inputs_col, inputs_row.t())

        epsilon = 1e-5
        loss = list()
        neg_count = 0
        for i in range(batch_size):
            pos_pair_ = torch.masked_select(sim_mat[i], target_row == targets_col[i])
            pos_pair_ = torch.masked_select(pos_pair_, pos_pair_ < 1 - epsilon)
            neg_pair_ = torch.masked_select(sim_mat[i], target_row != targets_col[i])

            # sampling step
            if self.hard_mining:
                neg_pair = neg_pair_[neg_pair_ + self.margin > torch.min(pos_pair_)]
                pos_pair = pos_pair_[pos_pair_ - self.margin < torch.max(neg_pair_)]

            if len(neg_pair) < 1 or len(pos_pair) < 1:
                continue
            neg_count += len(neg_pair)

            # weighting step
            pos_loss = (
                1.0
                / self.scale_pos
                * torch.log(
                    1 + torch.sum(torch.exp(-self.scale_pos * (pos_pair - self.thresh)))
                )
            )
            neg_loss = (
                1.0
                / self.scale_neg
                * torch.log(
                    1 + torch.sum(torch.exp(self.scale_neg * (neg_pair - self.thresh)))
                )
            )
            loss.append(pos_loss + neg_loss)

        if len(loss) == 0:
            return torch.zeros([], requires_grad=True).cuda()
        loss = sum(loss) / batch_size
        return loss

    def log_info(self, epoch, wandb):
        wandb.log({'neg_count': -1}, step=epoch)
