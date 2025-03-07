// document.addEventListener("DOMContentLoaded", function () {
//   const username = document.getElementById("socketUsername").value;
//   const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
//   const socket = new WebSocket(
//     `${protocol}//${window.location.host}/profile/${username}/`
//   );

//   socket.onopen = function () {
//   };

//   socket.onclose = function () {

//     // // 1) Create the HTML for your overlay + popup
//     // const overlayHTML = `
//     //   <div id="crew-updates-overlay" class="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-[9999]">
//     //     <div class="relative w-[400px] bg-white rounded-[10px] shadow-lg p-[20px] text-center">
//     //       <button id="closeOverlayBtn" 
//     //               class="absolute top-[10px] right-[10px] text-2xl border-none bg-none cursor-pointer">
//     //         &times;
//     //       </button>
//     //           <h4><strong>Live Updates are off!</strong></h4>
//     //     </div>
//     //   </div>
//     // `;

//     // // 2) Insert this HTML into the DOM
//     // document.body.insertAdjacentHTML("beforeend", overlayHTML);

//     // // 3) Attach close functionality to the button
//     // document.getElementById("closeOverlayBtn").onclick = function () {
//     //   document.getElementById("crew-updates-overlay").remove();
//     // };
//   };

//   socket.onmessage = function (event) {
//     location.reload();
//   };
// })




//coded in base JS for faster speed
document.addEventListener('DOMContentLoaded', function () {
    let all_events = JSON.parse(document.getElementById('pub_all_data').textContent); //using the json_script Django filter
    console.log(all_events)

    const pages = ~~(all_events.length/9) + 1; //note ~~ bitwise operator is limited to 32-bit integers but is faster than Math.trunc
    const pages_dump = document.getElementById('purchasedEventPages');
    let event_output = document.getElementById('purchasedEvents');


    renderEventAll(all_events);
    if (pages > 1) {
    renderPageAll();
    }

    function renderPageAll() {
        pages_dump.innerHTML = "";
        if (pages > 3) {
            for(i = 0; i < 3; i++) {    
                pages_dump.insertAdjacentHTML('beforeend',renderCount(i+1));
            }
            for(i = pages-3; i < pages; i++) {
                pages_dump.insertAdjacentHTML('beforeend',renderCount(i+1));
            }
        }
        else {
            for(i = 0; i < pages; i++) {    
                pages_dump.insertAdjacentHTML('beforeend',renderCount(i+1));
            }
        }
    }
    function renderEventAll(all, page=0) {
        let clean_output = event_output.cloneNode(false);
        event_output.parentElement.replaceChild(clean_output, event_output)
        event_output = clean_output
        i = page*9
        while(i < all.length && i < page*9+9) {
            html_event = renderEvent(all[i]);
            event_output.insertAdjacentHTML('beforeend',html_event);
            i+=1;
        }



    }
    let change_processing = false;
    eventChangeButtons =  document.querySelectorAll('.eventChange')
   Array.from(eventChangeButtons).forEach(button => {
    button.addEventListener('click', (e)=> {
        if(change_processing) {return;}
        change_processing = true;
        e.preventDefault();

        const btn = e.currentTarget;
        const page = btn.value;

        Array.from(eventChangeButtons).forEach(bootun => {bootun.classList.remove('active_page_btn');}) //bad
        btn.classList.add('active_page_btn')
        renderEventAll(all_events, page-1);
        change_processing = false;
    })
   })

   
    function renderEvent(event) {
        return `<a target="_blank" href="{% url 'core:eventDetails' eventId=${event.eventId} %}" class="category-event-card hover:category-image hover:scale-95 transform transition duration-300 flex flex-col justify-center items-center cursor-pointer overflow-hidden p-[10px] text-black">
        <div class="category-image w-full rounded-2xl shadow-custom-shadow-3">
            <img src=" ${event.header_photo_url}" alt="" class="w-full h-[200px] rounded-2xl rounded-b-none object-cover">
        </div>
        <div class="category-event-name font-Wanted-SemiBold text-Base flex flex-col justify-center items-start gap-1 w-full border border-custom-rgba5 rounded-bl-2xl rounded-br-2xl shadow-custom-shadow-3 border-t-2 px-5 p-2">
            <h2 id="eventTitle" class="whitespace-nowrap overflow-hidden text-ellipsis w-full text-left text-xl">${ event.title }</h2>
            <div class="eventSubInfo flex flex-col items-start gap-[1px] w-full font-Wanted-Variable text-customGray5">
                <p id="eventHost" class="flex flex-row justify-start">Hosted by @${ event.host_username }</p>
                <p id="eventDate" class="w-full flex justify-end font-Wanted-Bold text-Large">${ event.date }</p>
            </div>
        </div>
    </a>`;
    }

    function renderCount(count) {
        return  `<div class="border border-green rounded-2xl flex items-center">
                    <button type="button" class="eventChange w-full p-3 border rounded-2xl border-black bg-black text-white font-Wanted-Medium text-Semi-Medium cursor-pointer" value="${count}">
                        <span>${count}</span>
                    </button>
                </div>`;
    }

});









