document.addEventListener('DOMContentLoaded', function () {
  // Function to handle tab click with smooth transitions
  function handleTabClick(tab, tabContents) {
      // Remove active class from all tabs
      tab.forEach(tab => {
          tab.classList.remove('tab-active');
          tab.classList.remove('bg-green');
          tab.classList.remove('text-white');
          tab.classList.add('text-black');
          tab.classList.add('bg-white');
      });
      
      // Add active class to clicked tab
      this.classList.add('tab-active');
      this.classList.remove('bg-white');
      this.classList.add('bg-green');
      this.classList.remove('text-black');
      this.classList.add('text-white');

      // Get the tab ID from the clicked tab
      const tabId = this.getAttribute('data-tab');
      
      // Show the corresponding content
      showTabContent(tabContents, tabId);
      
      // Scroll to the content area (optional, for better UX)
      const contentArea = document.getElementById(tabId);
      if (contentArea) {
          // Add a small delay to ensure the content is visible first
          setTimeout(() => {
              contentArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }, 100);
      }
  }

  // Handle modal close buttons
  $("#closeCreateCollegeModalButton").on("click", function () {
    $("#preferencesModal").hide();
    $("#showTestPopup").show();
  });

  // Function to display corresponding content based on tab clicked
  function showTabContent(contents, tabId) {
      // First hide all content sections with a fade effect
      contents.forEach(content => {
          content.classList.add("hidden");
          content.style.opacity = 0;
      });

      // Then show the selected content with a fade-in effect
      const selectedTabContent = document.getElementById(tabId);
      if (selectedTabContent) {
          selectedTabContent.classList.remove("hidden");
          // Trigger reflow to ensure the transition works
          void selectedTabContent.offsetWidth;
          // Fade in the content
          setTimeout(() => {
              selectedTabContent.style.opacity = 1;
              selectedTabContent.style.transition = 'opacity 0.3s ease-in-out';
          }, 10);
      }
  }

  // Initialize tab systems for the main navigation (now in profileBody)
  initializeTabSystem("profileBody", "profile-tab", "profile-tab-content");

  // Initialize tab systems for nested tabs (like in My Events section)
  initializeTabSystem("myEvents-information", "myEvents-informationTab", "myEventsInformationContainer");

  // Function to initialize tab system for a specific body section
  function initializeTabSystem(bodyId, tabClass, contentClass) {
      const tabs = document.querySelectorAll(`#${bodyId} .${tabClass}`);
      const tabContents = document.querySelectorAll(`#${bodyId} .${contentClass}`);

      // Add click event listeners to all tabs
      tabs.forEach(tab => {
          tab.addEventListener('click', function () {
              handleTabClick.call(this, tabs, tabContents);
          });
          
          // Add hover effects
          tab.addEventListener('mouseenter', function() {
              if (!this.classList.contains('tab-active')) {
                  this.classList.add('shadow-md');
              }
          });
          
          tab.addEventListener('mouseleave', function() {
              if (!this.classList.contains('tab-active')) {
                  this.classList.remove('shadow-md');
              }
          });
      });

      // Make sure the first content is visible
      if (tabContents.length > 0) {
          tabContents[0].classList.remove("hidden");
          tabContents[0].style.opacity = 1;
      }

      // Set the first tab as active by default
      if (tabs.length > 0) {
          tabs[0].classList.add('tab-active');
          tabs[0].classList.remove('bg-white');
          tabs[0].classList.add('bg-green');
          tabs[0].classList.remove('text-black');
          tabs[0].classList.add('text-white');
          const defaultTabId = tabs[0].getAttribute('data-tab');
          showTabContent(tabContents, defaultTabId);
      }
  }
  
  // Add CSS for smooth transitions
  const style = document.createElement('style');
  style.textContent = `
    .profile-tab-content {
      transition: opacity 0.3s ease-in-out;
    }
    .profile-tab {
      transition: all 0.2s ease-in-out;
    }
    .tab-active {
      font-weight: 600;
    }
  `;
  document.head.appendChild(style);
});