"""MobileNetV3-small classifier for vehicle type recognition.

~2.5M parameters, runs on CPU in <50ms per inference.
4 output classes: three_wheeler, motorcycle, four_wheeler, unknown.
"""


def mobilenet_v3_classifier(num_classes: int = 4, pretrained: bool = True):
    """Build a MobileNetV3-small with a custom classifier head."""
    try:
        import torch
        import torch.nn as nn
        from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights

        weights = MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
        model = mobilenet_v3_small(weights=weights)
        in_features = model.classifier[0].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(in_features, num_classes),
        )
        return model
    except ImportError:
        return None
