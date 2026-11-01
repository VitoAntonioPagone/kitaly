(() => {
  const announcement = document.getElementById('cart-announcement');
  const italian = document.documentElement.lang.startsWith('it');
  let timeout;
  document.querySelectorAll('[data-cart-add]').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const button = form.querySelector('button');
      button.disabled = true;
      try {
        const response = await fetch(form.action, {method:'POST', body:new FormData(form), headers:{Accept:'application/json'}});
        if (!response.ok) throw new Error('unavailable');
        const result = await response.json();
        document.querySelectorAll('[data-cart-count]').forEach(count => { count.textContent=result.count; count.hidden=!result.count; });
        form.querySelector('[data-cart-label]').textContent=italian ? 'Nel carrello' : 'In your cart';
        form.querySelector('.cart-add__plus').textContent='✓';
        announcement.replaceChildren(document.createTextNode(result.message));
        const link=document.createElement('a'); link.href='/cart'; link.textContent=italian ? 'Vedi carrello' : 'View cart'; announcement.append(link);
      } catch (error) {
        announcement.textContent=italian ? 'Impossibile aggiungere questo articolo. Aggiorna la pagina e riprova.' : 'Unable to add this item. Refresh the page and try again.';
      } finally {
        button.disabled=false; announcement.hidden=false; clearTimeout(timeout);
        timeout=setTimeout(() => { announcement.hidden=true; },6000);
      }
    });
  });
})();
