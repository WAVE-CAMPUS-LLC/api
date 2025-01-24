// import { APILoader } from 'https://ajax.googleapis.com/ajax/libs/@googlemaps/extended-component-library/0.6.11/index.min.js';

// async function initMap() {
//     const { Autocomplete } = await APILoader.importLibrary('places');

//     // Reference the input element
//     const input = document.querySelector('.placesSearchInput');

//     // Initialize Autocomplete
//     const autocomplete = new Autocomplete(input, {
//         fields: ['formatted_address', 'geometry'],
//         types: ['address'],
//     });

//     // Listen for place selection
//     autocomplete.addListener('place_changed', () => {
//         const place = autocomplete.getPlace();

//         if (!place.geometry) {
//             alert(`No details available for input: '${place.name}'`);
//             return;
//         }

//         // Set the full address as the value of the input
//         input.value = place.formatted_address;

//         console.log('Selected Address:', place.formatted_address);
//         console.log('Latitude:', place.geometry.location.lat());
//         console.log('Longitude:', place.geometry.location.lng());
//     });
// }

// // Initialize the map on page load
// initMap();