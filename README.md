# Data Utils

A set of tools for collating and transferring datasets.

## Functions

1. Batch compression and decompression of datasets.

2. Send and receive files/directories.

## Features

1. Multithreaded compression and decompression with pigz.

2. Partitioning and merging of large datasets.

3. Send and receive files and check md5.

## Usage

### Compress & Decompress

**Compress a single dataset directory**

```bash
python utils/archive.py --src imagenet --dst . --split 2G
```

*Notice: If the dataset is larger than 2G, it will be divided into small files.*

**Decompress a single dataset**

```bash
python utils/archive.py --src imagenet.tar.gz --dst . --decompress
```

*Notice: If the source is a directory, it will be merged firstly.*

**Compress batch dataset directories**

```bash
python utils/archive.py --root datasets/ --dst tars/ --split 2G
```

*Notice: If the dataset is larger than 2G, it will be divided into small files.*

**Decompress batch datasets**

```bash
python util/archive.py --root tars/ --dst datasets/ --decompress
```

*Notice: If the dataset is larger than 2G, it will be divided into small files.*

### Send & Receive

**Send a single file**

```bash
python utils/remote.py --host 1.2.3.4 --port 1234 \
  --username user --password pass \
  --src file.txt --dst /dst/dir/
```

**Send a directory**

```bash
python utils/remote.py --host 1.2.3.4 --port 1234 \
  --username user --password pass \
  --src src/dir/ --dst /dst/dir/
```

**Receive a single file**

```bash
python utils/remote.py --host 1.2.3.4 --port 1234 \
  --username user --password pass \
  --src /src/dir/file.txt --dst . --receive
```

**Receive a directory**

```bash
python utils/remote.py --host 1.2.3.4 --port 1234 \
  --username user --password pass \
  --src /src/dir --dst . --receive
```

**Send/Recevice with config**

```bash
python utils/remote.py --config config.json --src src/dir/ --dst /dst/dir/
```

config.json should be like:

```json
{
    "host": "1.2.3.4",
    "port": 1234,
    "username": "user",
    "password": "pass"
}
```
