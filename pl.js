(async()=>{
  const chunks={
    monday:[
      "imgdata-hd/monday-1.txt",
      "imgdata-hd/monday-2.txt",
      "imgdata-hd/monday-3.txt"
    ],
    wednesday:[
      "imgdata-hd/wednesday-1.txt",
      "imgdata-hd/wednesday-2.txt",
      "imgdata-hd/wednesday-3.txt",
      "imgdata-hd/wednesday-4.txt"
    ],
    friday:[
      "imgdata-hd/friday-1.txt",
      "imgdata-hd/friday-2.txt",
      "imgdata-hd/friday-3.txt",
      "imgdata-hd/friday-4.txt"
    ]
  };

  const load=async(day,parts)=>{
    const img=document.getElementById("creative-img-"+day);
    if(!img) return;
    const texts=await Promise.all(parts.map(async p=>{
      const r=await fetch(p+"?v=4",{cache:"no-store"});
      if(!r.ok) throw new Error("No se pudo cargar "+p);
      return (await r.text()).trim();
    }));
    img.loading="eager";
    img.decoding="sync";
    img.src="data:image/avif;base64,"+texts.join("");
    try{await img.decode();}catch{}
  };

  try{
    await Promise.all(Object.entries(chunks).map(([day,parts])=>load(day,parts)));
  }catch(error){
    console.error(error);
  }

  const script=document.createElement("script");
  script.src="pl-core.js?v=4";
  script.async=false;
  document.body.appendChild(script);
})();