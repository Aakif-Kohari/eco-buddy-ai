import { useEffect } from "react"
import { Streamlit, withStreamlitConnection } from "streamlit-component-lib"
import { Canvas } from "@react-three/fiber"
import { OrbitControls, Box, Cylinder, Sphere } from "@react-three/drei"

function VirtualCity({ args }) {
  useEffect(() => {
    Streamlit.setFrameHeight(500)
  }, [])

  const assets = args?.unlocked_assets || []

  // A very simple procedural layout
  const renderAsset = (asset, index) => {
    // Determine position based on index to spread them out
    const x = (index % 5) * 2 - 4
    const z = Math.floor(index / 5) * 2 - 4

    switch (asset.type) {
      case "flora":
        return (
          <group key={index} position={[x, 0.5, z]}>
            <Cylinder args={[0.2, 0.2, 1]} args={[0.2, 0.2, 1]} material-color="brown" position={[0, -0.2, 0]} />
            <Sphere args={[0.8]} material-color="green" position={[0, 0.8, 0]} />
          </group>
        )
      case "energy":
        return (
          <group key={index} position={[x, 0.5, z]}>
            <Box args={[1, 0.1, 1]} material-color="blue" />
            <Cylinder args={[0.1, 0.1, 1]} material-color="gray" position={[0, -0.5, 0]} />
          </group>
        )
      case "building":
        return (
          <Box key={index} position={[x, 0.5, z]} args={[1, 1, 1]} material-color="white" />
        )
      case "terrain":
        return null // Ignore terrain here, we draw a generic ground
      default:
        return <Box key={index} position={[x, 0.5, z]} args={[0.5, 0.5, 0.5]} material-color="red" />
    }
  }

  return (
    <div style={{ height: "500px", width: "100%", background: "#87CEEB" }}>
      <Canvas camera={{ position: [0, 5, 10], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1} />
        
        {/* Ground */}
        <Box args={[20, 0.1, 20]} position={[0, -0.05, 0]} material-color="lightgreen" />
        
        {assets.map((asset, i) => renderAsset(asset, i))}
        
        <OrbitControls />
      </Canvas>
    </div>
  )
}

export default withStreamlitConnection(VirtualCity)
