<form id="wishlistForm">
  <input type="text" name="item_name" required>
  <input type="text" name="item_details" required>
  <button type="submit">Add to Wishlist</button>
</form>

<script>
  document.getElementById('wishlistForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const data = {
      item_name: form.item_name.value,
      item_details: form.item_details.value
    };

    const res = await fetch(form.action, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    const result = await res.json();
    console.log(result);
  });
</script>
