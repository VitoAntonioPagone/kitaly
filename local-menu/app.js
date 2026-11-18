/* Local prototype only. All collection filtering stays in this page. */
const dialog=document.querySelector('dialog');
const trigger=document.querySelector('.menu-trigger');
const close=document.querySelector('.close-menu');
let language='en',theme='light',products=[],selection='all';
const labels={all:['The Stock','Lo Stock'],player:['Player Issue','Player Issue'],national:['National teams','Nazionali']};
function openMenu(){dialog.showModal();trigger.setAttribute('aria-expanded','true');close.focus()}
trigger.addEventListener('click',openMenu);
close.addEventListener('click',()=>dialog.close());
dialog.addEventListener('close',()=>{trigger.setAttribute('aria-expanded','false');trigger.focus({preventScroll:true})});
dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close()});
function renderProducts(){
  const shown=products.filter(p=>selection==='all'||selection==='player'&&p.player||selection==='national'&&p.national||p.league===selection);
  document.querySelector('#collection-title').textContent=labels[selection]?.[language==='en'?0:1]||selection;
  document.querySelector('#results').textContent=`${shown.length} ${language==='en'?'items':'articoli'}`;
  const grid=document.querySelector('#products');grid.replaceChildren();
  for(const p of shown){const article=document.createElement('article'),image=document.createElement('img'),name=document.createElement('h2'),price=document.createElement('p');image.src=p.image;image.alt=p.name;name.textContent=p.name;price.textContent=p.price;article.append(image,name,price);grid.append(article)}
  if(!shown.length){const p=document.createElement('p');p.className='empty-state';p.textContent=language==='en'?'No shirts in this preview selection. Choose All stock to see the sample catalogue.':'Nessuna maglia in questa selezione di anteprima. Scegli Tutto lo stock per vedere il catalogo di esempio.';grid.append(p)}
}
document.querySelectorAll('[data-collection],[data-league]').forEach(link=>link.addEventListener('click',event=>{event.preventDefault();selection=link.dataset.collection||link.dataset.league;document.querySelectorAll('[data-collection],[data-league]').forEach(item=>item.removeAttribute('aria-current'));const active=document.querySelector(`.navigation-columns [data-collection="${selection}"],.navigation-columns [data-league="${selection}"],.all-stock[data-collection="${selection}"]`);active?.setAttribute('aria-current','page');history.replaceState(null,'',link.getAttribute('href'));renderProducts();dialog.close()}));
document.querySelectorAll('[data-language]').forEach(button=>button.addEventListener('click',()=>{language=button.dataset.language;document.documentElement.lang=language;document.querySelectorAll('[data-en]').forEach(e=>e.textContent=e.dataset[language]);document.querySelectorAll('[data-label-en]').forEach(e=>e.setAttribute('aria-label',e.dataset[language==='en'?'labelEn':'labelIt']));document.querySelectorAll('[data-language]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));renderProducts()}));
document.querySelectorAll('[data-theme]').forEach(button=>button.addEventListener('click',()=>{theme=button.dataset.theme;document.documentElement.classList.toggle('dark',theme==='dark');document.querySelectorAll('[data-theme]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)))}));
fetch('assets/products.json').then(r=>{if(!r.ok)throw new Error('Catalogue unavailable');return r.json()}).then(items=>{products=items;renderProducts()}).catch(()=>{document.querySelector('#results').textContent='Preview catalogue unavailable'});
openMenu();
