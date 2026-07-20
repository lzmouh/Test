
"""
Sensor Retrieval Tool - Proof-of-Concept Simulation Dashboard
"""

import matplotlib.pyplot as plt

contact_area=[3,4,5,6,7,8,9,10]
velocity_area=[3.2,2.9,2.5,2.1,1.8,1.5,1.2,0.9]
esp_rate=[750,1000,1500,2000,2500,3000]
velocity_esp=[0.9,1.5,2.6,3.6,4.6,5.6]
density=[1.0,1.2,1.4,1.6,1.8,2.0]
velocity_density=[4.1,3.6,3.0,2.4,1.8,1.2]
api=[25,30,35,40,45,50,55]
velocity_api=[1.7,2.0,2.3,2.6,2.9,3.2,3.4]
viscosity=[2,5,10,20,30]
velocity_vis=[3.6,3.2,2.7,2.0,1.5]
diameter=[1.5,1.75,2.0,2.25,2.5]
velocity_diameter=[4.1,3.6,3.0,2.3,1.7]
length=[4,6,8,10,12]
velocity_length=[3.3,3.0,2.8,2.6,2.4]
depth=[1000,2000,3000,4000,5000]
retrieval_depth=[5.6,11.1,16.7,22.2,27.8]
retrieval_rate=[80,55,32,23,18,15]

plots=[
("Figure 1. Effect of Contact Surface Area on Tool Lifting Velocity",contact_area,velocity_area,"Projected Contact Surface Area (in²)","Average Lifting Velocity (ft/s)","Increasing contact area increases drag.","Simulation"),
("Figure 2. Effect of ESP Production Rate on Tool Lifting Velocity",esp_rate,velocity_esp,"ESP Production Rate (BPD)","Average Lifting Velocity (ft/s)","Higher ESP rate increases lift.","Simulation"),
("Figure 3. Effect of Tool Density on Lifting Velocity",density,velocity_density,"Tool Density (g/cm³)","Average Lifting Velocity (ft/s)","Higher density lowers lift.","Simulation"),
("Figure 4. Effect of Oil API Gravity on Tool Lifting Velocity",api,velocity_api,"Oil API Gravity (°API)","Average Lifting Velocity (ft/s)","Lighter oil improves retrieval.","Simulation"),
("Figure 5. Effect of Oil Viscosity on Tool Lifting Velocity",viscosity,velocity_vis,"Oil Viscosity (cP)","Average Lifting Velocity (ft/s)","Higher viscosity reduces speed.","Simulation"),
("Figure 6. Effect of Tool Diameter on Lifting Velocity",diameter,velocity_diameter,"Tool Diameter (in.)","Average Lifting Velocity (ft/s)","Larger diameter increases drag.","Simulation"),
("Figure 7. Effect of Tool Length on Lifting Velocity",length,velocity_length,"Tool Length (in.)","Average Lifting Velocity (ft/s)","Length has smaller influence.","Simulation"),
("Figure 8. Effect of Well Depth on Retrieval Time",depth,retrieval_depth,"Well Depth (ft)","Estimated Retrieval Time (min)","Travel time rises with depth.","Simulation"),
("Figure 9. Effect of ESP Production Rate on Retrieval Time",esp_rate,retrieval_rate,"ESP Production Rate (BPD)","Estimated Retrieval Time (min)","Higher ESP rate shortens retrieval.","Simulation")
]

fig,axs=plt.subplots(3,3,figsize=(16,12))
fig.suptitle("Proof-of-Concept Simulation of Downhole Sensor Retrieval Tool\nVertical ESP Well - 5000 ft Depth",
fontsize=18,fontweight='bold')

for ax,p in zip(axs.flat,plots):
    title,x,y,xl,yl,note,leg=p
    ax.plot(x,y,marker='o',linewidth=2,label=leg)
    ax.set_title(title,fontsize=10,fontweight='bold')
    ax.set_xlabel(xl,fontsize=9)
    ax.set_ylabel(yl,fontsize=9)
    ax.grid(True,linestyle='--',alpha=0.6)
    ax.minorticks_on()
    ax.legend(loc='best',fontsize=8)
    ax.text(0.03,0.04,note,transform=ax.transAxes,fontsize=8,
            bbox=dict(facecolor='white',alpha=0.8))

fig.text(0.5,0.015,
"Reference Conditions: Vertical well • 5000 ft TVD • Tubing ID 3 in • Tool Ø2 in × 6 in • Density 1.5 g/cm³ • Oil API 50° • Simplified force-balance model.\nResults are illustrative proof-of-concept only.",
ha='center',fontsize=9)

plt.tight_layout(rect=[0,0.05,1,0.94])
plt.savefig("Sensor_Retrieval_Simulation_Dashboard.png",dpi=300)
plt.savefig("Sensor_Retrieval_Simulation_Dashboard.pdf")
plt.savefig("Sensor_Retrieval_Simulation_Dashboard.svg")
plt.show()
