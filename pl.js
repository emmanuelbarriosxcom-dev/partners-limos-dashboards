(async()=>{
  const sources={
    monday:"assets/pl-rrss-07-11-sep-26-mon.avif?v=3",
    wednesday:"assets/pl-rrss-07-11-sep-26-wed.avif?v=3",
    friday:"assets/pl-rrss-07-11-sep-26-fri.avif?v=3"
  };
  const load=(day,src)=>new Promise((resolve,reject)=>{
    const img=document.getElementById("creative-img-"+day);
    if(!img){resolve();return;}
    let settled=false;
    const done=()=>{if(settled)return;settled=true;resolve();};
    const fail=()=>{if(settled)return;settled=true;reject(new Error("No se pudo cargar la imagen de "+day));};
    img.loading="eager";
    img.decoding="async";
    img.onload=done;
    img.onerror=fail;
    img.src=src;
    if(img.complete&&img.naturalWidth) done();
  });
  try{await Promise.all(Object.entries(sources).map(([day,src])=>load(day,src)));}catch(error){console.error(error);}
  const script=document.createElement("script");
  script.src="pl-core.js?v=3";
  script.async=false;
  document.body.appendChild(script);
})();