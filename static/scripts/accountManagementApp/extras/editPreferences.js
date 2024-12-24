document.addEventListener('DOMContentLoaded', function() {
    const displays = document.querySelectorAll('#display');
    const edits = document.querySelectorAll('#edit');

    const editPreferencesButton = document.getElementById('edit-preferences-button');
    const editPreferencesDiv = document.getElementById('edit-preferences-div');
    
    const cancelSavePreferences = document.getElementById('cancel-save-preferences');
    
    const cancelEditPreferencesButton = document.getElementById('cancel-preferences-button');


    editPreferencesButton.addEventListener('click', function() {
        displays.forEach(display => display.classList.add('hidden'));
        edits.forEach(edit => edit.classList.remove('hidden'));
        editPreferencesDiv.classList.add('hidden');
        cancelSavePreferences.classList.remove('hidden');
    });

    cancelEditPreferencesButton.addEventListener('click', function() {
        displays.forEach(display => display.classList.remove('hidden'));
        edits.forEach(edit => edit.classList.add('hidden'));
        editPreferencesDiv.classList.remove('hidden');
        cancelSavePreferences.classList.add('hidden');
    });
});