function loadVehicleDetails(index, vehicles, vehicle_images) {
    const selectedVehicle = vehicles[index - 1];
    const detailsContainer = document.getElementById('vehicleDetails');
    const galleryContainer = document.getElementById('imageGallery');

    const detailsHTML = `
        <h2>Details for ${selectedVehicle.reg}</h2>
        <p>VIN: ${selectedVehicle.vin}</p>
        <p>Make: ${selectedVehicle.make}</p>
        <p>Model: ${selectedVehicle.model}</p>
        <!-- Add more details as needed -->
    `;
    detailsContainer.innerHTML = detailsHTML;

    // Filter vehicle images for the selected vehicle
    const selectedVehicleImages = vehicle_images.filter(image => image['vehicle-id'] === selectedVehicle.vh_id);

    let galleryHTML = '<h2>Image Gallery</h2><div class="gallery">';

    selectedVehicleImages.forEach(image => {
        galleryHTML += `
            <img src="${image['image-url']}" alt="${image['filename']}" class="gallery-image">
            <!-- You can add more image details if needed -->
        `;
    });
    galleryHTML += '</div>';
    galleryContainer.innerHTML = galleryHTML;
}
