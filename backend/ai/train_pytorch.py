import logging
import os
from datetime import datetime, timezone

import cv2


logger = logging.getLogger(__name__)


def train_pytorch(
    images_dir: str,
    model_output_path: str,
    num_epochs: int = 20,
    batch_size: int = 16,
    learning_rate: float = 0.001,
) -> dict:
    """Train a MobileNetV3-small classifier, export to TorchScript.

    Args:
        images_dir: Directory with labeled subdirectories (class names as folder names)
        model_output_path: Where to save the TorchScript model
        num_epochs: Training epochs
        batch_size: Batch size for training
        learning_rate: AdamW learning rate

    Returns:
        dict with success, accuracy, samples, classes
    """
    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from torch.utils.data import Dataset, DataLoader
        from torchvision import transforms
    except ImportError:
        return {
            "success": False,
            "error": "PyTorch not installed. Install with: pip install retromind[torch]",
        }

    from ai.models.cnn_model import mobilenet_v3_classifier

    class _ImageDataset(Dataset):
        def __init__(self, root_dir, transform=None):
            self.samples = []
            self.classes = sorted([
                d for d in os.listdir(root_dir)
                if os.path.isdir(os.path.join(root_dir, d))
            ])
            self.class_to_idx = {c: i for i, c in enumerate(self.classes)}
            self.transform = transform or transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])

            for cls_name in self.classes:
                cls_dir = os.path.join(root_dir, cls_name)
                for fname in os.listdir(cls_dir):
                    if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                        self.samples.append((
                            os.path.join(cls_dir, fname),
                            self.class_to_idx[cls_name],
                        ))

        def __len__(self):
            return len(self.samples)

        def __getitem__(self, idx):
            path, label = self.samples[idx]
            img = cv2.imread(path)
            if img is None:
                return self.__getitem__((idx + 1) % len(self.samples))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = self.transform(img)
            return img, label

    dataset = _ImageDataset(images_dir)
    if len(dataset) < 10:
        return {
            "success": False,
            "error": f"Not enough samples ({len(dataset)}). Need at least 10.",
        }

    model = mobilenet_v3_classifier(num_classes=len(dataset.classes), pretrained=True)
    if model is None:
        return {"success": False, "error": "Failed to create model"}

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=learning_rate)

    model.train()
    for epoch in range(num_epochs):
        total_loss = 0.0
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        if (epoch + 1) % 5 == 0:
            logger.info("Epoch %d/%d, loss=%.4f", epoch + 1, num_epochs, total_loss)

    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = torch.max(outputs, 1)
            correct += (predicted == labels).sum().item()
            total += labels.size(0)

    accuracy = correct / max(total, 1)

    scripted_model = torch.jit.script(model.cpu())
    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    scripted_model.save(model_output_path)
    logger.info("PyTorch model saved to %s (accuracy=%.4f)", model_output_path, accuracy)

    return {
        "success": True,
        "accuracy": round(accuracy, 4),
        "samples": len(dataset),
        "classes": dataset.classes,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_path": model_output_path,
        "device": str(device),
    }
