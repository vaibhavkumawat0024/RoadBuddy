// State Management
let currentState = null;
let currentPlaceName = "";
let currentPlaceCategory = "";
let favorites = [];

// Fallback Unsplash image IDs by category to guarantee beautiful results
const categoryBgs = {
  "Hill Station": "1605649487212-47bdab064df7", // Himachal mountains
  "Temple": "1584551246679-0daf3d275d0f", // South Indian temple
  "Beach": "1507525428034-b723cf961d3e", // Goa Beach
  "Heritage": "1564507592333-c60657eea523", // Taj Mahal
  "Wildlife": "1615715036162-88b8162eeaa5", // Elephant/forest
  "Adventure": "1597079910300-4b0d00f707f1", // River/rafting
  "Nature": "1506461883276-594a12b11cc3" // Munnar hills
};

// DOM Elements
const bg1 = document.getElementById("bg-1");
const bg2 = document.getElementById("bg-2");
const searchInput = document.getElementById("search-input");
const suggestionsBox = document.getElementById("suggestions");
const statesCarousel = document.getElementById("states-carousel");
const sidebarPlacesList = document.getElementById("sidebar-places-list");

const placeTitle = document.getElementById("place-title");
const placeState = document.getElementById("place-state");
const placeCategory = document.getElementById("place-category");
const placeDesc = document.getElementById("place-desc");
const itineraryTimeline = document.getElementById("itinerary-timeline");

const btnToggleFav = document.getElementById("btn-toggle-fav");
const btnFavorites = document.getElementById("btn-favorites");
const favCount = document.getElementById("fav-count");
const favoritesDrawer = document.getElementById("favorites-drawer");
const closeDrawer = document.getElementById("close-drawer");
const drawerItems = document.getElementById("drawer-items");
const drawerOverlay = document.getElementById("drawer-overlay");
const btnWiki = document.getElementById("btn-wiki");
const categoryButtons = document.querySelectorAll(".cat-btn");

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
  // Load Favorites from LocalStorage
  if (localStorage.getItem("bharat_itineraries")) {
    favorites = JSON.parse(localStorage.getItem("bharat_itineraries"));
    updateFavoritesUI();
  }

  // Render State Selector Carousel
  renderStatesCarousel();

  // Set default view (Himachal Pradesh -> Manali)
  selectState("himachal-pradesh");
  selectPlace("Manali", "Hill Station");

  // Event Listeners
  setupEventListeners();
  lucide.createIcons();
});

// Setup Event Listeners
function setupEventListeners() {
  // Search Input
  searchInput.addEventListener("input", handleSearchInput);
  document.addEventListener("click", (e) => {
    if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
      suggestionsBox.style.display = "none";
    }
  });

  // Drawer Toggle
  btnFavorites.addEventListener("click", () => toggleDrawer(true));
  closeDrawer.addEventListener("click", () => toggleDrawer(false));
  drawerOverlay.addEventListener("click", () => toggleDrawer(false));

  // Favorites Add/Remove Action
  btnToggleFav.addEventListener("click", toggleFavoriteCurrent);

  // Category filter strip actions
  categoryButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      categoryButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const selectedCat = btn.getAttribute("data-cat");
      filterSidebarPlaces(selectedCat);
    });
  });
}

// Render the States Bottom Carousel
function renderStatesCarousel() {
  statesCarousel.innerHTML = "";
  statesData.forEach(state => {
    const card = document.createElement("div");
    card.className = "state-card";
    card.setAttribute("data-id", state.id);
    
    // Background Unsplash URL for State
    const imgUrl = `https://images.unsplash.com/photo-${state.imgId}?auto=format&fit=crop&w=300&q=80`;
    
    card.innerHTML = `
      <div class="state-card-bg" style="background-image: url('${imgUrl}');"></div>
      <div class="state-card-overlay">
        <h4>${state.name}</h4>
        <span>10 Places</span>
      </div>
    `;

    card.addEventListener("click", () => {
      document.querySelectorAll(".state-card").forEach(c => c.classList.remove("active"));
      card.classList.add("active");
      selectState(state.id);
    });

    statesCarousel.appendChild(card);
  });
}

// Select a State and load its sidebar tourist places
function selectState(stateId) {
  const state = statesData.find(s => s.id === stateId);
  if (!state) return;
  currentState = state;

  // Active state in carousel
  document.querySelectorAll(".state-card").forEach(card => {
    if (card.getAttribute("data-id") === stateId) {
      card.classList.add("active");
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    } else {
      card.classList.remove("active");
    }
  });

  // Reset category filter strip to "All"
  categoryButtons.forEach(b => b.classList.remove("active"));
  document.querySelector('[data-cat="All"]').classList.add("active");

  renderSidebarPlaces(state.places);
  
  // Select first place of state by default
  const firstPlace = state.places[0];
  selectPlace(firstPlace[0], firstPlace[1]);
}

// Render Places in Sidebar
function renderSidebarPlaces(placesList) {
  sidebarPlacesList.innerHTML = "";
  placesList.forEach(place => {
    const item = document.createElement("div");
    item.className = "place-item";
    item.setAttribute("data-name", place[0]);
    item.innerHTML = `
      <span>${place[0]}</span>
      <span class="tag">${place[1]}</span>
    `;

    item.addEventListener("click", () => {
      selectPlace(place[0], place[1]);
    });

    sidebarPlacesList.appendChild(item);
  });
}

// Filter Sidebar Places by Category
function filterSidebarPlaces(category) {
  const items = sidebarPlacesList.querySelectorAll(".place-item");
  let firstVisible = null;

  items.forEach((item, index) => {
    const placeName = item.getAttribute("data-name");
    const placeData = currentState.places.find(p => p[0] === placeName);
    
    if (category === "All" || placeData[1] === category) {
      item.style.display = "flex";
      if (!firstVisible) firstVisible = placeData;
    } else {
      item.style.display = "none";
    }
  });

  // Auto select first visible place in filter
  if (firstVisible) {
    selectPlace(firstVisible[0], firstVisible[1]);
  }
}

// Change Fullscreen Background with smooth cross-fade
function changeBackground(placeName, category) {
  // Try to fetch custom query from LoremFlickr, fallback to Unsplash Category ID
  const query = `${placeName.split(' ')[0]},india`;
  const mainUrl = `https://loremflickr.com/1600/1000/${encodeURIComponent(query)}`;
  
  // Fallback URL
  const fallbackImgId = categoryBgs[category] || "1506461883276-594a12b11cc3";
  const fallbackUrl = `https://images.unsplash.com/photo-${fallbackImgId}?auto=format&fit=crop&w=1600&q=80`;

  // Find active and inactive panels
  const activePanel = bg1.classList.contains("active") ? bg1 : bg2;
  const inactivePanel = activePanel === bg1 ? bg2 : bg1;

  // Create temporary image object to preload before showing
  const imgLoader = new Image();
  imgLoader.src = mainUrl;

  imgLoader.onload = () => {
    inactivePanel.style.backgroundImage = `url('${mainUrl}')`;
    swapPanels();
  };

  imgLoader.onerror = () => {
    // If Flickr search fails or is slow, load the beautiful Unsplash fallback
    inactivePanel.style.backgroundImage = `url('${fallbackUrl}')`;
    swapPanels();
  };

  function swapPanels() {
    activePanel.classList.remove("active");
    inactivePanel.classList.add("active");
  }
}

// Select a Place to display Itinerary and background
function selectPlace(placeName, category) {
  currentPlaceName = placeName;
  currentPlaceCategory = category;

  // Highlight active place in sidebar
  const items = sidebarPlacesList.querySelectorAll(".place-item");
  items.forEach(item => {
    if (item.getAttribute("data-name") === placeName) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Update text elements
  placeTitle.textContent = placeName;
  placeState.textContent = currentState.name;
  placeCategory.textContent = category;
  placeCategory.style.borderColor = category === "Temple" ? "rgba(255,153,51,0.4)" : "rgba(56,189,248,0.4)";
  
  // Dynamic description
  placeDesc.textContent = `Explore the best of ${placeName}, a beautiful ${category.toLowerCase()} in ${currentState.name}. Experience local culture, sights, and landmarks.`;

  // Render Itinerary Timeline
  renderItinerary(placeName, category);

  // Smoothly update background photo
  changeBackground(placeName, category);

  // Update Favorite Action Button state
  updateFavoriteBtnState();

  // Wikipedia Link
  btnWiki.href = `https://en.wikipedia.org/wiki/${encodeURIComponent(placeName)}`;
}

// Programmatic Template Itinerary Generator (token-efficient)
function renderItinerary(placeName, category) {
  itineraryTimeline.innerHTML = "";
  
  const itineraries = {
    "Hill Station": [
      { title: "Arrival & Pine Forests", desc: `Arrive in ${placeName}. Check in to your resort, relax, and explore local cafes and pine-fringed walks in the evening.` },
      { title: "Sightseeing & Valley View", desc: `Wake up early to view the sunrise. Spend the day trekking, paragliding, or exploring key vantage points and water bodies.` },
      { title: "Souvenir Shopping & Departure", desc: "Visit local craft markets, purchase organic tea/spices, and check out with gorgeous memories." }
    ],
    "Temple": [
      { title: "Spiritual Entry & Evening Aarti", desc: `Arrive at the holy town of ${placeName}. Settle in and attend the grand evening prayer service or Ganga Aarti.` },
      { title: "Darshan & Historical Courtyards", desc: "Participate in early morning Darshan/Abhishek. Walk through medieval stone-carved temple complexes with a local guide." },
      { title: "Museums & Local Markets", desc: "Explore cultural museums, buy traditional brass idols or prayer items, and begin your return journey." }
    ],
    "Beach": [
      { title: "Sunsets & Sea Shacks", desc: `Check in to a beach resort in ${placeName}. Relax on the sand, watch the sunset, and enjoy local seafood at seaside shacks.` },
      { title: "Water Sports & Boat Safari", desc: "Enjoy banana boat rides, jet-skiing, or parasailing. Take an afternoon boat cruise to spot dolphins or nearby forts." },
      { title: "Cliffs, Lighthouses & Depart", desc: "Take a morning jog along coastal paths, climb the local lighthouse for panoramic sea views, and checkout." }
    ],
    "Heritage": [
      { title: "Grand Forts & Light Show", desc: `Reach ${placeName}. Explore the massive courtyards and palaces. Catch the history-rich sound & light show in the evening.` },
      { title: "Guided Architecture Tour", desc: "Spend the day analyzing intricate carvings, visiting stepwells, and taking incredible photographs of history." },
      { title: "Bazaar Crafts & Departure", desc: "Browse local markets for block prints, artifacts, or traditional jewelry before checking out." }
    ],
    "Wildlife": [
      { title: "Jungle Lodge & Nature Trail", desc: `Arrive at the sanctuary gates of ${placeName}. Check into a forest lodge and take an afternoon guided bird-watching walk.` },
      { title: "Morning Tiger/Fauna Safari", desc: "Set off on an early morning open-jeep safari. Spot native animals, explore dense woods, and take raw nature photos." },
      { title: "Conservation Centers & Return", desc: "Visit the local animal rehabilitation center, learn about flora species, and depart." }
    ],
    "Adventure": [
      { title: "Camp check-in & Accclimatization", desc: `Reach the base camp of ${placeName}. Meet instructors, inspect safety gear, and undergo briefing by campfire.` },
      { title: "Rafting / Paragliding / Peak Hike", desc: "Challenge yourself with river rafting, paragliding, or peak climbing activities under expert supervision." },
      { title: "Trek Down & Souvenirs", desc: "Finish the adventure loop, celebrate with a group lunch, and collect souvenirs before driving back." }
    ],
    "Nature": [
      { title: "Arrival & Scenic Walks", desc: `Arrive at ${placeName}. Check in to your cottage, sip local herbal tea, and walk through scenic plantations or lakeshores.` },
      { title: "Waterfalls & Viewpoints", desc: "Explore local waterfalls, caves, and viewpoints. Take a serene boat ride or trek through lush valleys." },
      { title: "Flora Gardens & Departure", desc: "Visit botanical nurseries, buy native handloom or organic goods, and checkout." }
    ]
  };

  // Fallback to "Nature" if category not matched
  const steps = itineraries[category] || itineraries["Nature"];

  steps.forEach((step, idx) => {
    const dayBox = document.createElement("div");
    dayBox.className = "day-box";
    dayBox.innerHTML = `
      <div class="day-num">Day ${idx + 1}</div>
      <div class="day-details">
        <h4>${step.title}</h4>
        <p>${step.desc}</p>
      </div>
    `;
    itineraryTimeline.appendChild(dayBox);
  });
}

// Search box handling
function handleSearchInput(e) {
  const query = e.target.value.toLowerCase().trim();
  if (query.length < 2) {
    suggestionsBox.style.display = "none";
    return;
  }

  suggestionsBox.innerHTML = "";
  let matches = [];

  // Match states and destinations
  statesData.forEach(state => {
    if (state.name.toLowerCase().includes(query)) {
      matches.push({ type: "state", name: state.name, id: state.id });
    }
    state.places.forEach(place => {
      if (place[0].toLowerCase().includes(query)) {
        matches.push({ type: "place", name: place[0], category: place[1], stateId: state.id, stateName: state.name });
      }
    });
  });

  // Slice to top 6 matches to fit screen beautifully
  matches.slice(0, 6).forEach(match => {
    const div = document.createElement("div");
    div.className = "suggestion-item";
    
    if (match.type === "state") {
      div.innerHTML = `<span><strong>${match.name}</strong> (State)</span><span class="suggestion-state">Capital: ${statesData.find(s=>s.id===match.id).capital}</span>`;
      div.addEventListener("click", () => {
        selectState(match.id);
        searchInput.value = match.name;
        suggestionsBox.style.display = "none";
      });
    } else {
      div.innerHTML = `<span><strong>${match.name}</strong></span><span class="suggestion-state">${match.stateName} (${match.category})</span>`;
      div.addEventListener("click", () => {
        selectState(match.stateId);
        selectPlace(match.name, match.category);
        searchInput.value = match.name;
        suggestionsBox.style.display = "none";
      });
    }
    suggestionsBox.appendChild(div);
  });

  suggestionsBox.style.display = matches.length > 0 ? "block" : "none";
}

// Trip Favorites Drawer Drawer Toggle
function toggleDrawer(open) {
  if (open) {
    favoritesDrawer.classList.add("open");
    drawerOverlay.classList.add("active");
    renderDrawerItems();
  } else {
    favoritesDrawer.classList.remove("open");
    drawerOverlay.classList.remove("active");
  }
}

// Add/remove favorite from database
function toggleFavoriteCurrent() {
  const existingIdx = favorites.findIndex(f => f.name === currentPlaceName);
  if (existingIdx > -1) {
    favorites.splice(existingIdx, 1);
  } else {
    favorites.push({
      name: currentPlaceName,
      state: currentState.name,
      category: currentPlaceCategory
    });
  }

  localStorage.setItem("bharat_itineraries", JSON.stringify(favorites));
  updateFavoritesUI();
  updateFavoriteBtnState();
}

function updateFavoriteBtnState() {
  const exists = favorites.some(f => f.name === currentPlaceName);
  if (exists) {
    btnToggleFav.innerHTML = `<i data-lucide="check"></i> Added to Trip`;
    btnToggleFav.style.background = "var(--accent-green)";
  } else {
    btnToggleFav.innerHTML = `<i data-lucide="heart"></i> Add to Trip`;
    btnToggleFav.style.background = "var(--accent-gold)";
  }
  lucide.createIcons();
}

function updateFavoritesUI() {
  favCount.textContent = favorites.length;
}

function renderDrawerItems() {
  drawerItems.innerHTML = "";
  if (favorites.length === 0) {
    drawerItems.innerHTML = `<p style="color: var(--text-secondary); text-align: center; margin-top: 2rem;">No places added yet. Select destinations to build your itinerary!</p>`;
    return;
  }

  favorites.forEach(fav => {
    const item = document.createElement("div");
    item.className = "fav-item";
    item.innerHTML = `
      <div class="fav-details">
        <h4>${fav.name}</h4>
        <span>${fav.state} (${fav.category})</span>
      </div>
      <button class="delete-fav" data-name="${fav.name}"><i data-lucide="trash-2"></i></button>
    `;

    // Click on fav item loads it
    item.addEventListener("click", (e) => {
      if (e.target.closest(".delete-fav")) return;
      const stateObj = statesData.find(s => s.name === fav.state);
      if (stateObj) {
        toggleDrawer(false);
        selectState(stateObj.id);
        selectPlace(fav.name, fav.category);
      }
    });

    // Delete item handler
    item.querySelector(".delete-fav").addEventListener("click", () => {
      favorites = favorites.filter(f => f.name !== fav.name);
      localStorage.setItem("bharat_itineraries", JSON.stringify(favorites));
      updateFavoritesUI();
      renderDrawerItems();
      if (fav.name === currentPlaceName) {
        updateFavoriteBtnState();
      }
    });

    drawerItems.appendChild(item);
  });
  lucide.createIcons();
}
