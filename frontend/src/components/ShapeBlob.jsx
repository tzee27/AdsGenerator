import '../styles/ShapeBlob.css';

const shapes = {
  blob1: 'polygon(30% 0%, 70% 5%, 100% 30%, 95% 70%, 65% 100%, 25% 95%, 0% 65%, 5% 25%)',
  blob2: 'polygon(50% 0%, 90% 20%, 100% 60%, 75% 100%, 25% 100%, 0% 60%, 10% 20%)',
  blob3: 'polygon(20% 0%, 80% 0%, 100% 20%, 100% 80%, 80% 100%, 20% 100%, 0% 80%, 0% 20%)',
  blob4: 'polygon(40% 0%, 100% 10%, 100% 90%, 60% 100%, 0% 85%, 0% 15%)',
  blob5: 'polygon(0% 30%, 30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%)',
  blob6: 'polygon(15% 0%, 85% 5%, 100% 50%, 85% 95%, 15% 100%, 0% 50%)',
};

export default function ShapeBlob({ variant = 'blob1', size = 200, opacity = 0.5, color = 'surface', style = {} }) {
  const clipPath = shapes[variant] || shapes.blob1;

  return (
    <div
      className={`shape-blob shape-blob--${color}`}
      style={{
        width: size,
        height: size,
        clipPath,
        opacity,
        ...style,
      }}
    />
  );
}
