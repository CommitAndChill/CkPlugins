"""Quantize original PNG16 encoded RGB to PNG8 without gamma/grade/resizing.

Only creates RuntimeV2/BaseColor.png and Manifest-runtime-v2.json. Source maps,
the source generator receipt and the original manifest remain byte-identical.
Uses exact stdlib PNG unfiltering because Pillow truncates RGB16 on decode.
"""
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import zlib
sys.dont_write_bytecode=True
import numpy as np
from PIL import Image, PngImagePlugin
import source_batch2_textures as source

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'Plugins/CkTests/Resources/CkUsf/PebbleReferenceV1'


def decode16(data):
    if data[:8]!=b'\x89PNG\r\n\x1a\n':raise RuntimeError('PNG signature missing')
    offset=8;compressed=[];metadata={}
    while offset<len(data):
        size=struct.unpack('>I',data[offset:offset+4])[0];tag=data[offset+4:offset+8];body=data[offset+8:offset+8+size]
        crc=struct.unpack('>I',data[offset+8+size:offset+12+size])[0]
        if zlib.crc32(tag+body)&0xffffffff!=crc:raise RuntimeError('PNG CRC mismatch')
        if tag==b'IHDR':width,height,depth,kind,compression,filtering,interlace=struct.unpack('>IIBBBBB',body)
        elif tag==b'IDAT':compressed.append(body)
        elif tag in [b'gAMA',b'sRGB']:metadata[tag]=body
        offset+=size+12
        if tag==b'IEND':break
    if depth!=16 or kind not in [2,6] or compression!=0 or filtering!=0 or interlace!=0:
        raise RuntimeError('Expected noninterlaced RGB/RGBA16 standard PNG')
    channels=4 if kind==6 else 3;bpp=channels*2;stride=width*bpp
    raw=zlib.decompress(b''.join(compressed))
    if len(raw)!=(stride+1)*height:raise RuntimeError('PNG decompressed dimensions mismatch')
    rows=np.empty((height,stride),dtype=np.uint8);previous=bytearray(stride)
    for y in range(height):
        start=y*(stride+1);method=raw[start];row=bytearray(raw[start+1:start+1+stride])
        if method==1:
            # Each byte lane has an independent modulo256 prefix sum.
            a=np.frombuffer(row,dtype=np.uint8).reshape(width,bpp)
            row=bytearray(np.cumsum(a,axis=0,dtype=np.uint32).astype(np.uint8).tobytes())
        elif method==2:
            row=bytearray((np.frombuffer(row,dtype=np.uint8).astype(np.uint16)+np.frombuffer(previous,dtype=np.uint8)).astype(np.uint8).tobytes())
        elif method in [3,4]:
            for x in range(stride):
                left=row[x-bpp] if x>=bpp else 0;up=previous[x]
                if method==3:predict=(left+up)//2
                else:
                    corner=previous[x-bpp] if x>=bpp else 0;p=left+up-corner
                    pa,pb,pc=abs(p-left),abs(p-up),abs(p-corner)
                    predict=left if pa<=pb and pa<=pc else up if pb<=pc else corner
                row[x]=(row[x]+predict)&255
        elif method!=0:raise RuntimeError('Unsupported PNG filter')
        rows[y]=np.frombuffer(row,dtype=np.uint8);previous=row
    values=np.frombuffer(rows.tobytes(),dtype='>u2').astype(np.uint16).reshape(height,width,channels)
    return values,metadata


def main():
    original_manifest=OUTPUT/'Manifest.json';manifest_data=original_manifest.read_bytes();manifest=json.loads(manifest_data)
    maps=manifest['materials']['pebbles']['maps'];bc=maps['BaseColor'];original=OUTPUT/bc['path'];original_bytes=original.read_bytes()
    if source.sha256(original_bytes)!=bc['sha256']:raise RuntimeError('Pinned source16BC changed')
    values,metadata=decode16(original_bytes)
    if values.shape[2]==4 and not np.all(values[:,:,3]==65535):raise RuntimeError('Unexpected nonopaque source alpha')
    rgb=values[:,:,:3]
    quantized=((rgb.astype(np.uint32)+128)//257).astype(np.uint8)
    error=np.abs(quantized.astype(np.float64)/255-rgb.astype(np.float64)/65535)
    if error.max()>.5/255+1e-12:raise RuntimeError('EncodedRGB quantization bound exceeded')
    png_info=PngImagePlugin.PngInfo()
    for key,body in metadata.items():png_info.add(key,body)
    image=Image.fromarray(quantized);buffer=io.BytesIO();image.save(buffer,format='PNG',compress_level=9,pnginfo=png_info)
    data=buffer.getvalue();relative='pebbles/RuntimeV2/BaseColor.png';path=OUTPUT/relative;source.immutable(path,data)
    if not np.array_equal(np.asarray(Image.open(path).convert('RGB')),quantized):raise RuntimeError('PNG8 roundtrip mismatch')
    entry=source.image_info(data,'BaseColor',relative,'EnvironmentRiverPebblesBC8')
    entry.update(source_url=bc['source_url'],modifications='Exact16bitPNG unfilter then encodedRGB8=round(encodedRGB16/257); opaquealpha dropped. No gamma transform, color grade, resampling or spatial changes.',source_sha256=bc['sha256'])
    new=json.loads(manifest_data);new['materials']['pebbles']['maps']['BaseColor']=entry
    new['source_manifest']={'path':'Manifest.json','sha256':source.sha256(manifest_data),'generator_source':manifest['generator_source'],'generator_sha256':manifest['generator_sha256']}
    new['runtime_color_derivation']={'recipe_source':'Tools/UsfMaterials/derive_pebble_runtime_color.py','recipe_sha256':source.sha256(Path(__file__).read_bytes()),'source_path':bc['path'],'source_sha256':bc['sha256'],'source_bit_depth':16,'source_channels':int(values.shape[2]),'source_encoded_RGB_mean':(rgb.astype(np.float64)/65535).mean(axis=(0,1)).tolist(),'runtime_bit_depth':8,'runtime_name':entry['runtime_name'],'quantization':'q8=floor((q16+128)/257), normalizedencodederror<=0.5/255','max_encoded_error':float(error.max()),'mean_encoded_error':float(error.mean()),'gamma_transform':False,'resize':False,'original_opaque_alpha':True,'retained_color_chunks':{key.decode():body.hex() for key,body in metadata.items()},'intent':'Isolated nativeimport A/B candidate addressing16bit-vs8bit source decode; no Unrealacceptance or causalfix claim.'}
    for channel in ['Normal','Roughness','Height','AO']:
        if new['materials']['pebbles']['maps'][channel]!=maps[channel] or source.sha256((OUTPUT/maps[channel]['path']).read_bytes())!=maps[channel]['sha256']:
            raise RuntimeError('Unrelated source map changed: '+channel)
    if original_manifest.read_bytes()!=manifest_data or original.read_bytes()!=original_bytes:raise RuntimeError('Original provenance/source changed')
    target=OUTPUT/'Manifest-runtime-v2.json';source.immutable(target,(json.dumps(new,indent=2,sort_keys=True)+'\n').encode())
    print(json.dumps({'manifest_sha256':source.sha256(target.read_bytes()),'runtime_BC_sha256':entry['sha256'],'recipe_sha256':new['runtime_color_derivation']['recipe_sha256'],'max_encoded_error':float(error.max()),'dimensions':[int(rgb.shape[1]),int(rgb.shape[0])],'runtime_name':entry['runtime_name']},indent=2))


if __name__=='__main__':main()
