let quill; // Declare the quill instance globally

document.addEventListener('DOMContentLoaded', () => {
  quill = new Quill('#quill-editor', {
    theme: 'snow',
    modules: {
      toolbar: [
        ['bold', 'italic', 'underline'],
        ['link', 'blockquote', 'code-block'],
        [{ list: 'ordered' }, { list: 'bullet' }],
        [{ header: [1, 2, 3, false] }],
        [{ align: [] }],
        ['clean'],
      ],
    },
  });

  // Synchronize Quill with hidden textarea
  const eventDescriptionTextarea = document.getElementById('id_description');
  quill.on('text-change', () => {
    eventDescriptionTextarea.value = quill.root.innerHTML;
  });
});
