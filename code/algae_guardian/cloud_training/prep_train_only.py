import os, sys
sys.path.insert(0, "/data/algae_guardian")
from cloud_training.prepare_lifewatch import create_yolo_dataset, build_class_mapping
cm, cn = build_class_mapping("/data/datasets/lifewatch/dataset_files_equal/classes.txt", "/data/datasets/lifewatch")
print(f"Classes: {len(cn)}")
create_yolo_dataset("/data/datasets/lifewatch", "/data/lifewatch_yolo", ["train"], cn)
print("DONE")
