/* MD5 byte-string digest for RouterOS HTTP-CHAP only. Uses raw 8-bit bytes.
 * CHAP hashes the router challenge ID + password + challenge in that order.
 * Do not use MD5 for storing passwords or any general security purpose. */
(function(root){
  function md5(raw){
    var bytes=[],i,j;
    raw=String(raw);
    for(i=0;i<raw.length;i++)bytes.push(raw.charCodeAt(i)&255);
    var originalLength=bytes.length;
    bytes.push(128);
    while(bytes.length%64!==56)bytes.push(0);
    var bitLo=(originalLength*8)>>>0;
    var bitHi=Math.floor(originalLength/0x20000000)>>>0;
    for(i=0;i<4;i++)bytes.push((bitLo>>>(8*i))&255);
    for(i=0;i<4;i++)bytes.push((bitHi>>>(8*i))&255);
    var a=0x67452301,b=0xefcdab89,c=0x98badcfe,d=0x10325476;
    var shifts=[7,12,17,22,5,9,14,20,4,11,16,23,6,10,15,21];
    function rol(x,n){return (x<<n)|(x>>>(32-n));}
    for(i=0;i<bytes.length;i+=64){
      var word=[];
      for(j=0;j<16;j++)word[j]=(bytes[i+4*j]|(bytes[i+4*j+1]<<8)|(bytes[i+4*j+2]<<16)|(bytes[i+4*j+3]<<24))>>>0;
      var A=a,B=b,C=c,D=d;
      for(j=0;j<64;j++){
        var f,g,q;
        if(j<16){f=(B&C)|((~B)&D);g=j;q=shifts[j%4];}
        else if(j<32){f=(D&B)|((~D)&C);g=(5*j+1)%16;q=shifts[4+j%4];}
        else if(j<48){f=B^C^D;g=(3*j+5)%16;q=shifts[8+j%4];}
        else{f=C^(B|(~D));g=(7*j)%16;q=shifts[12+j%4];}
        var k=Math.floor(Math.abs(Math.sin(j+1))*4294967296);
        var oldD=D;
        D=C;C=B;
        B=(B+rol((A+f+k+word[g])|0,q))|0;
        A=oldD;
      }
      a=(a+A)|0;b=(b+B)|0;c=(c+C)|0;d=(d+D)|0;
    }
    var out='';
    var words=[a,b,c,d];
    for(i=0;i<4;i++)for(j=0;j<4;j++){
      var hex=((words[i]>>>(8*j))&255).toString(16);
      out+=(hex.length<2?'0':'')+hex;
    }
    return out;
  }
  root.hotChapMd5=md5;
  if(typeof module!=='undefined'&&module.exports)module.exports=md5;
})(this);
