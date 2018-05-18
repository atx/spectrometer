
difference() {
	minkowski() {
		cube([16, 16, 6], center=true);
		cylinder(r=2, h=0.01, $fn=100);
	}
	translate([0, 0, -0.5])
		cube([17, 15.5, 4], center=true);
	translate([0, 0, 2])
		cube([9, 3, 5], center=true);
}
