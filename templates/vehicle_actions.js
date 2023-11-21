function addVehicle(index, vehicles) {
    const selectedVehicle = vehicles[index - 1];

    // Redirect to the add vehicle route with the registration number as a parameter
    window.location.href = `/add_vehicle/${selectedVehicle.reg}`;
}
