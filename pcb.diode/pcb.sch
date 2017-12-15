EESchema Schematic File Version 2
LIBS:power
LIBS:device
LIBS:transistors
LIBS:conn
LIBS:linear
LIBS:regul
LIBS:74xx
LIBS:cmos4000
LIBS:adc-dac
LIBS:memory
LIBS:xilinx
LIBS:microcontrollers
LIBS:dsp
LIBS:microchip
LIBS:analog_switches
LIBS:motorola
LIBS:texas
LIBS:intel
LIBS:audio
LIBS:interface
LIBS:digital-audio
LIBS:philips
LIBS:display
LIBS:cypress
LIBS:siliconi
LIBS:opto
LIBS:atmel
LIBS:contrib
LIBS:valves
LIBS:sma
LIBS:pcb-cache
EELAYER 25 0
EELAYER END
$Descr A4 11693 8268
encoding utf-8
Sheet 1 1
Title ""
Date ""
Rev ""
Comp ""
Comment1 ""
Comment2 ""
Comment3 ""
Comment4 ""
$EndDescr
$Comp
L SMA J1
U 1 1 5A1938D0
P 2450 2625
F 0 "J1" H 2600 2525 59  0000 C CNN
F 1 "SMA" H 2450 2775 59  0000 C CNN
F 2 "local:SMA_STRAIGHT_PCB_LPRS" H 2450 2425 197 0001 C CNN
F 3 "" H 2450 2425 197 0000 C CNN
	1    2450 2625
	1    0    0    -1  
$EndComp
$Comp
L D_Photo_ALT D1
U 1 1 5A19395C
P 3375 2725
F 0 "D1" H 3395 2795 50  0000 L CNN
F 1 "X100" H 3335 2615 50  0000 C CNN
F 2 "local:X100-7-THD" H 3325 2725 50  0001 C CNN
F 3 "" H 3325 2725 50  0001 C CNN
	1    3375 2725
	0    1    1    0   
$EndComp
Wire Wire Line
	2450 2825 2450 2950
Wire Wire Line
	2450 2950 3375 2950
Wire Wire Line
	3375 2950 3375 2825
Wire Wire Line
	3375 2525 3375 2500
Wire Wire Line
	3375 2500 2975 2500
Wire Wire Line
	2975 2500 2975 2625
Wire Wire Line
	2975 2625 2700 2625
$Comp
L TEST S1
U 1 1 5A193E80
P 2525 3175
F 0 "S1" H 2525 3475 50  0000 C BNN
F 1 "M2" H 2525 3425 50  0000 C CNN
F 2 "Measurement_Points:Measurement_Point_Round-TH_Big" H 2525 3175 50  0001 C CNN
F 3 "" H 2525 3175 50  0001 C CNN
	1    2525 3175
	-1   0    0    1   
$EndComp
$Comp
L TEST S2
U 1 1 5A193F66
P 2725 3175
F 0 "S2" H 2725 3475 50  0000 C BNN
F 1 "M2" H 2725 3425 50  0000 C CNN
F 2 "Measurement_Points:Measurement_Point_Round-TH_Big" H 2725 3175 50  0001 C CNN
F 3 "" H 2725 3175 50  0001 C CNN
	1    2725 3175
	-1   0    0    1   
$EndComp
Wire Wire Line
	2525 3175 2525 2950
Connection ~ 2525 2950
Wire Wire Line
	2725 3175 2725 2950
Connection ~ 2725 2950
$EndSCHEMATC
