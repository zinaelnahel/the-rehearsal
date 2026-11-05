const fs=require('node:fs');
const {parse}=require('next/dist/compiled/babel/parser');
const catalog=JSON.parse(fs.readFileSync('app/locales.json','utf8'));
const missing=new Set();
const preserved=new Set(['https://www.idealista.com/inmueble/…/']);
for(const filename of fs.readdirSync('app').filter(f=>f.endsWith('.js')&&f!=='i18n.js')){
 const ast=parse(fs.readFileSync('app/'+filename,'utf8'),{sourceType:'module',plugins:['jsx']});
 function visit(node){
  if(!node||typeof node!=='object')return;
  if(node.type==='JSXAttribute'&&node.name?.name==='value'&&node.value?.type==='JSXExpressionContainer'
     &&node.value.expression.type==='CallExpression'&&node.value.expression.callee?.name==='t'){
   missing.add(filename+': controlled values must use canonical state, not translated labels');
  }
  if((node.type==='JSXText'||node.type==='StringLiteral')&&/Espa\?ol/.test(node.value||'')){
   missing.add(filename+': Spanish must be spelled Español');
  }
  if(node.type==='CallExpression'&&node.callee?.name==='t'&&node.arguments[0]?.type==='StringLiteral'){
   const key=node.arguments[0].value.trim();
   if(!catalog[key]&&!preserved.has(key))missing.add(filename+': '+key);
  }
  for(const [key,value] of Object.entries(node)){
   if(['loc','extra','comments'].includes(key))continue;
   if(Array.isArray(value))value.forEach(visit);else if(value&&typeof value==='object')visit(value);
  }
 }
 visit(ast);
}
for(const [key,translations] of Object.entries(catalog)){
 const placeholders=text=>(text.match(/\{[a-zA-Z_]+\}/g)||[]).sort().join(',');
 for(const locale of ['de','es'])if(!translations[locale]?.trim()||placeholders(key)!==placeholders(translations[locale]))missing.add(locale+': incomplete translation or placeholders for '+key);
}
if(missing.size){console.error([...missing].join('\n'));process.exit(1);}
console.log('Translation coverage and placeholders passed: '+Object.keys(catalog).length+' messages in DE/ES.');
