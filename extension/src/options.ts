document.getElementById('origin')!.textContent = chrome.runtime.getURL('').replace(/\/$/, '');
document.getElementById('pair')!.addEventListener('submit', async event => {
  event.preventDefault();
  const input = document.getElementById('token') as HTMLInputElement;
  await chrome.storage.local.setAccessLevel({ accessLevel: 'TRUSTED_CONTEXTS' });
  await chrome.storage.local.set({ token: input.value });
  input.value = '';
  document.getElementById('status')!.textContent = 'Pairing saved. Open your configured Yahoo league; the sidebar will check the connection.';
});
