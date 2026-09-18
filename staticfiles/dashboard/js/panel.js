// Shows the chosen file in the preview next to a file input before saving.
document.querySelectorAll('input[type="file"][data-preview]').forEach((input) => {
  const preview = input.closest('.upload')?.querySelector('.upload__preview');
  if (!preview) return;

  input.addEventListener('change', () => {
    const [file] = input.files;
    if (!file || !file.type.startsWith('image/')) return;
    if (preview.dataset.objectUrl) URL.revokeObjectURL(preview.dataset.objectUrl);
    const url = URL.createObjectURL(file);
    preview.dataset.objectUrl = url;
    preview.src = url;
    preview.hidden = false;
  });
});
