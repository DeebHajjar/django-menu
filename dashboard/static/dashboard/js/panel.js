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

/*
 * Rows that can be added without saving first.
 *
 * A formset marked `data-formset="<prefix>"` carries a <template> holding
 * Django's empty form, with `__prefix__` where the row number goes. Adding a
 * row copies that markup, numbers it, and tells the management form there is
 * one more. Removing a row added this way simply drops it: the gap it leaves
 * is a form with no data, which Django ignores.
 *
 * Without JavaScript the rows the server rendered still work, so the form is
 * never broken by this being absent.
 */
document.querySelectorAll('[data-formset]').forEach((formset) => {
  const prefix = formset.dataset.formset;
  const rows = formset.querySelector('[data-formset-rows]');
  const template = formset.querySelector('[data-formset-template]');
  const addButton = formset.querySelector('[data-formset-add]');
  const total = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
  if (!rows || !template || !addButton || !total) return;

  const maximum = document.getElementById(`id_${prefix}-MAX_NUM_FORMS`);

  function atCeiling() {
    const limit = Number(maximum?.value);
    return Number.isFinite(limit) && limit > 0 && Number(total.value) >= limit;
  }

  /** A fresh row, numbered, straight from the template. */
  function buildRow(index) {
    const holder = document.createElement('div');
    holder.innerHTML = template.innerHTML.replaceAll('__prefix__', String(index));
    const row = holder.firstElementChild;
    if (row) row.dataset.formsetIndex = String(index);
    return row;
  }

  addButton.hidden = false;

  addButton.addEventListener('click', () => {
    if (atCeiling()) return;

    const index = Number(total.value);
    const row = buildRow(index);
    if (!row) return;

    rows.append(row);
    total.value = String(index + 1);
    addButton.disabled = atCeiling();

    // Land in the new row, so several can be added straight after each other.
    row.querySelector('select, input:not([type="hidden"])')?.focus();
  });

  rows.addEventListener('click', (event) => {
    const button = event.target.closest('[data-formset-remove]');
    if (!button) return;
    // Only rows added here: a saved row is removed with its own checkbox.
    const row = button.closest('[data-formset-new]');
    if (!row) return;

    /*
     * The row keeps its number and is put back the way it arrived, then
     * hidden. Taking it out of the page altogether would leave a gap, and a
     * gap is not an empty form to Django — it is a form missing required
     * values, which fails the whole save. Sent back untouched, it is skipped.
     */
    const fresh = buildRow(row.dataset.formsetIndex);
    if (!fresh) return;
    fresh.hidden = true;
    row.replaceWith(fresh);
  });
});
