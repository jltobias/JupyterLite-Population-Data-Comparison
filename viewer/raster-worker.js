/* Local files only. GeoTIFF.js 3.0.5, MIT; see vendor/geotiff notices. */
importScripts('vendor/geotiff/geotiff-3.0.5.js');
const LIMIT=262144, MAX_BLOCK_PIXELS=16777216;
const finite=Number.isFinite;
// Bound metadata work before GeoTIFF.js walks any image directories.
async function preflight(file){
  let bytes=0;
  async function read(offset,size){if(!Number.isSafeInteger(offset)||!Number.isSafeInteger(size)||offset<0||size<0||offset+size>file.size||(bytes+=size)>8*1024*1024)throw Error('TIFF metadata exceeds bounds or the 8 MiB budget.');return new DataView(await file.slice(offset,offset+size).arrayBuffer());}
  const head=await read(0,Math.min(16,file.size)),order=head.getUint16(0),little=order===0x4949;
  if(!little&&order!==0x4d4d)throw Error('Invalid TIFF byte order.');
  if(!little)throw Error('Big-endian TIFF is unsupported by this pinned reader; prepare a little-endian excerpt.');
  const version=head.getUint16(2,little),big=version===43;
  if(version!==42&&!big)throw Error('Invalid TIFF version.');
  if(big&&(head.getUint16(4,little)!==8||head.getUint16(6,little)!==0))throw Error('Unsupported BigTIFF header.');
  const number=(view,at,size)=>{const value=size===8?Number(view.getBigUint64(at,little)):view.getUint32(at,little);if(!Number.isSafeInteger(value))throw Error('TIFF offset/count exceeds safe integer range.');return value;};
  let offset=number(head,big?8:4,big?8:4),seen=new Set(),directories=0;
  const sizes={1:1,2:1,3:2,4:4,5:8,6:1,7:1,8:2,9:4,10:8,11:4,12:8,13:4,16:8,17:8,18:8};
  while(offset){
    if(seen.has(offset)||++directories>32)throw Error('TIFF directory loop or more than 32 directories.');seen.add(offset);
    const countSize=big?8:2,entrySize=big?20:12,pointerSize=big?8:4;
    const first=await read(offset,countSize),count=big?number(first,0,8):first.getUint16(0,little);
    if(count>1024)throw Error('TIFF directory exceeds 1024 metadata entries.');
    const entries=await read(offset+countSize,count*entrySize+pointerSize);
    for(let i=0;i<count;i++){
      const at=i*entrySize,tag=entries.getUint16(at,little),type=entries.getUint16(at+2,little),length=number(entries,at+4,big?8:4)*sizes[type];
      if(tag===330)throw Error('SubIFD rasters/masks are unsupported.');
      if(!Number.isSafeInteger(length)||length>4*1024*1024)throw Error('Unsupported TIFF metadata type/size.');
      if(length>pointerSize){const dataOffset=number(entries,at+(big?12:8),pointerSize);if(dataOffset+length>file.size)throw Error('TIFF metadata points outside the file.');bytes+=length;if(bytes>8*1024*1024)throw Error('TIFF metadata exceeds the 8 MiB budget.');}
    }
    offset=number(entries,count*entrySize,pointerSize);
  }
  if(!directories)throw Error('TIFF has no primary image.');
}
const limitError=()=>Error('Decoded TIFF block exceeds its declared native size.');
// Adapted from the pinned companion's MIT bounded LZW decoder.
function boundedLZW(buffer,size){
  const input=new Uint8Array(buffer),output=new Uint8Array(size),prefix=new Uint16Array(4096),suffix=new Uint8Array(4096),stack=new Uint8Array(4096);
  let bit=0,width=9,next=258,old=-1,first=0,position=0;
  const emit=value=>{if(position>=size)throw limitError();output[position++]=value;};
  while(bit+width<=input.length*8){
    let code=0;for(let i=0;i<width;i++,bit++)code=code*2+((input[bit>>3]>>(7-bit%8))&1);
    if(code===257){if(position!==size)throw Error('Incomplete LZW block.');return output.buffer;}
    if(code===256){width=9;next=258;old=-1;continue;}
    const current=code;let top=0;
    if(code===next&&old>=0){stack[top++]=first;code=old;}else if(code>=next)throw Error('Invalid LZW block.');
    while(code>=258){if(top>=4095)throw Error('Invalid LZW dictionary.');stack[top++]=suffix[code];code=prefix[code];}
    if(code>255)throw Error('Invalid LZW code.');first=code;stack[top++]=first;while(top)emit(stack[--top]);
    if(old>=0&&next<4096){prefix[next]=old;suffix[next++]=first;if(next===(1<<width)-1&&width<12)width++;}old=current;
  }
  throw Error('Incomplete LZW block.');
}
self.onmessage=async ({data:{file,bounds}})=>{
  try {
    if(!(file instanceof Blob)||file.size>2**31)throw Error('Choose a TIFF file of at most 2 GiB.');
    if(!Array.isArray(bounds)||bounds.length!==4||!bounds.every(finite)||!(bounds[0]<bounds[2]&&bounds[1]<bounds[3]&&bounds[0]>=-180&&bounds[2]<=180&&bounds[1]>=-90&&bounds[3]<=90))throw Error('Select valid WGS84 import bounds.');
    await preflight(file);
    const tiff=await GeoTIFF.fromBlob(file), count=await tiff.getImageCount();
    if(count>32)throw Error('TIFF has too many image directories.');
    for(let i=0;i<count;i++){
      const candidate=await tiff.getImage(i), d=candidate.getFileDirectory(),kind=d.getValue('NewSubfileType')||0;
      if(kind&4)throw Error('Internal masks are unsupported; use a file with declared NoData.');
      if(i>0&&!(kind&1))throw Error('Multiple primary images are unsupported.');
    }
    const image=await tiff.getImage(0), d=image.getFileDirectory(), keys=await image.getGeoKeys();
    if(image.getSamplesPerPixel()!==1||(await d.loadValue('ExtraSamples'))?.length)throw Error('Only one count band without alpha/extra samples is supported.');
    if(keys?.GeographicTypeGeoKey!==4326||keys?.GTModelTypeGeoKey!==2||keys.ProjectedCSTypeGeoKey)throw Error('Only explicitly declared geographic EPSG:4326 TIFFs are supported.');
    if(keys.GeogAngularUnitsGeoKey&&keys.GeogAngularUnitsGeoKey!==9102)throw Error('WGS84 coordinates must use angular degrees.');
    if(keys.GTRasterTypeGeoKey!==1)throw Error('Only PixelIsArea rasters are supported.');
    const transform=await d.loadValue('ModelTransformation'),scale=await d.loadValue('ModelPixelScale'),tie=await d.loadValue('ModelTiepoint');
    if(transform||!scale||!tie||tie.length!==6)throw Error('Only north-up scale/tiepoint geometry is supported; rotated transforms are rejected.');
    const [dx,dy]=scale,[i,j,k,x,y,z]=tie;
    if(![dx,dy,i,j,x,y].every(finite)||dx<=0||dy<=0||dx>5||dy>5||k!==0||z!==0)throw Error('Unsupported TIFF transform.');
    const west=x-i*dx,north=y+j*dy,width=image.getWidth(),height=image.getHeight();
    if(!Number.isSafeInteger(width)||!Number.isSafeInteger(height)||width<1||height<1||west< -180||west+width*dx>180.00000001||north>90||north-height*dy< -90.00000001)throw Error('TIFF dimensions or geographic extent are invalid.');
    const raw=String(await d.loadValue('GDAL_METADATA')||'');
    const metadata=await image.getGDALMetadata(0)||{}, allMetadata=await image.getGDALMetadata()||{};
    if(Object.keys({...allMetadata,...metadata}).some(key=>/scale|offset/i.test(key))||/(?:name|role)\s*=\s*["'][^"']*(?:scale|offset)[^"']*["']/i.test(raw))throw Error('TIFF scale/offset metadata is unsupported; counts must be stored directly.');
    const rawNoData=await d.loadValue('GDAL_NODATA');
    if(rawNoData!==undefined&&rawNoData!==null){
      const lexical=String(rawNoData).replace(/\0+$/,'').trim();
      if(!/^[+-]?nan$/i.test(lexical)&&(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(lexical)||!finite(Number(lexical))))throw Error('Invalid raw NoData declaration; use a finite numeric sentinel or nan.');
    }
    const nodata=image.getGDALNoData();
    if(nodata!==null&&!finite(nodata)&&!Number.isNaN(nodata))throw Error('Invalid NoData declaration.');
    const x0=Math.max(0,Math.min(width,Math.floor((bounds[0]-west)/dx))),x1=Math.max(0,Math.min(width,Math.ceil((bounds[2]-west)/dx)));
    const y0=Math.max(0,Math.min(height,Math.floor((north-bounds[3])/dy))),y1=Math.max(0,Math.min(height,Math.ceil((north-bounds[1])/dy)));
    if(x1<=x0||y1<=y0)throw Error('Selected area lies outside this TIFF.');
    if((x1-x0)*(y1-y0)>LIMIT)throw Error(`Selected native window exceeds ${LIMIT} cells. Choose smaller import bounds; no resampling is performed.`);
    const bits=image.getBitsPerSample(),format=image.getSampleFormat(),compression=d.getValue('Compression')||1,predictor=d.getValue('Predictor')||1;
    if(!([1,2].includes(format)?[8,16,32]:format===3?[32,64]:[]).includes(bits)||![1,5,8,32946].includes(compression)||(d.getValue('Orientation')||1)!==1||![0,1].includes(d.getValue('PhotometricInterpretation')??1)||![1,2,3].includes(predictor)||(predictor===2&&bits===64)||(predictor===3&&format!==3))throw Error('Unsupported sample encoding, compression, predictor, color or orientation. Use integer/float counts with uncompressed, LZW or Deflate encoding.');
    const blockWidth=image.getTileWidth(),blockHeight=image.getTileHeight();
    const declaredDimensions=image.isTiled?[d.getValue('TileWidth'),d.getValue('TileLength')]:[d.getValue('RowsPerStrip')??height];
    if([...declaredDimensions,blockWidth,blockHeight].some(value=>!Number.isSafeInteger(value)||value<=0))throw Error('TIFF tile/strip dimensions must be positive integers.');
    if(blockWidth*blockHeight>MAX_BLOCK_PIXELS)throw Error('TIFF decode blocks exceed the 16 million-pixel memory limit; prepare a tiled excerpt first.');
    const blocks=(Math.ceil(x1/blockWidth)-Math.floor(x0/blockWidth))*(Math.ceil(y1/blockHeight)-Math.floor(y0/blockHeight));
    if(blocks*blockWidth*blockHeight*bits/8>128*1024*1024)throw Error('Selected window requires more than 128 MiB of decoded source blocks; prepare a tiled excerpt first.');
    const byteCounts=await d.loadValue(image.isTiled?'TileByteCounts':'StripByteCounts'),offsets=await d.loadValue(image.isTiled?'TileOffsets':'StripOffsets'),across=Math.ceil(width/blockWidth);
    let compressed=0;
    for(let by=Math.floor(y0/blockHeight);by<Math.ceil(y1/blockHeight);by++)for(let bx=Math.floor(x0/blockWidth);bx<Math.ceil(x1/blockWidth);bx++){
      const index=by*across+bx,size=Number(byteCounts?.[index]),offset=Number(offsets?.[index]);
      if(!Number.isSafeInteger(size)||!Number.isSafeInteger(offset)||size<0||offset<0||offset+size>file.size||(size===0)!==(offset===0)||(compressed+=size)>64*1024*1024)throw Error('Selected TIFF blocks exceed file bounds or the 64 MiB compressed budget.');
    }
    const output=Array((x1-x0)*(y1-y0)).fill(null);
    for(let by=Math.floor(y0/blockHeight);by<Math.ceil(y1/blockHeight);by++)for(let bx=Math.floor(x0/blockWidth);bx<Math.ceil(x1/blockWidth);bx++){
      const part=[Math.max(x0,bx*blockWidth),Math.max(y0,by*blockHeight),Math.min(x1,(bx+1)*blockWidth),Math.min(y1,(by+1)*blockHeight)],sparse=Number(byteCounts[by*across+bx])===0,blockBytes=blockWidth*image.getBlockHeight(by)*bits/8;
      class Decoder extends GeoTIFF.BaseDecoder{
        async decodeBlock(buffer){
          if(compression===5)return boundedLZW(buffer,blockBytes);
          if(compression===1){if(buffer.byteLength!==blockBytes)throw limitError();return buffer;}
          const reader=new Blob([buffer]).stream().pipeThrough(new DecompressionStream('deflate')).getReader(),decoded=new Uint8Array(blockBytes);let at=0;
          while(true){const {done,value}=await reader.read();if(done)break;if(at+value.length>blockBytes){await reader.cancel();throw limitError();}decoded.set(value,at);at+=value.length;}
          if(at!==blockBytes)throw Error('Incomplete Deflate block.');return decoded.buffer;
        }
      }
      const values=sparse?null:await image.readRasters({window:part,samples:[0],interleave:true,pool:{bindParameters:(_,params)=>new Decoder(params)}});
      let at=0;for(let row=part[1];row<part[3];row++)for(let column=part[0];column<part[2];column++){
        const value=sparse?(nodata??0):values[at++];
        if(nodata!==null&&(Number.isNaN(nodata)?Number.isNaN(value):value===nodata))continue;
        if(!finite(value)||value<0)throw Error('Native window contains negative or nonfinite counts not declared as NoData.');
        output[(row-y0)*(x1-x0)+column-x0]=value;
      }
    }
    self.postMessage({grid:{width:x1-x0,height:y1-y0,west:west+x0*dx,north:north-y0*dy,dx,dy,values:output},file_declarations:{name:file.name,size:file.size,last_modified:file.lastModified,source_dimensions:[width,height],source_grid:{west,north,dx,dy},native_window:[x0,y0,x1,y1],nodata:Number.isNaN(nodata)?'NaN':nodata,geo_keys:keys,gdal_metadata:allMetadata,band_metadata:metadata,mask_policy:'No internal mask/alpha accepted. External .msk sidecars are not read; user must declare none.',reader:'GeoTIFF.js 3.0.5',processing:'Local-file native window; no resampling, scale, reprojection or server computation'}});
  } catch(error){self.postMessage({error:error.message});}
};
