import { Link } from 'react-router-dom';
import type { Product } from '../types';

interface ProductCardProps {
  product: Product;
}

export default function ProductCard({ product }: ProductCardProps) {
  const hasDiscount = product.discount_percent && product.discount_percent > 0;

  return (
    <Link
      to={`/product/${product.id}`}
      className="block glass-card overflow-hidden"
    >
      <div className="p-4">
        <h3 className="text-sm font-medium text-white/90 line-clamp-2 min-h-[2.5rem]">
          {product.name}
        </h3>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-lg font-bold text-red-600">
            ${product.price?.toLocaleString() ?? '—'}
          </span>
          {product.original_price && product.original_price > (product.price ?? 0) && (
            <span className="text-sm text-white/30 line-through">
              ${product.original_price.toLocaleString()}
            </span>
          )}
          {hasDiscount && (
            <span className="text-xs bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded font-medium">
              -{product.discount_percent}%
            </span>
          )}
        </div>
        <div className="mt-2 flex items-center gap-3 text-xs text-white/40">
          {product.brand && <span>{product.brand}</span>}
          {product.category && <span>{product.category}</span>}
        </div>
      </div>
    </Link>
  );
}
