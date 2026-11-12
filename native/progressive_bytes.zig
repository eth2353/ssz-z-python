//! Preserve the JSON distinction between ProgressiveList[Byte] (hex) and
//! ProgressiveList[uint8] (array), which share the same SSZ representation.
const ssz = @import("ssz");
const Base = ssz.FixedProgressiveListType(ssz.UintType(8));

pub const Type = struct {
    pub const is_bytes = true;
    pub const kind = Base.kind;
    pub const Element = Base.Element;
    pub const Type = Base.Type;
    pub const min_size = Base.min_size;
    pub const max_size = Base.max_size;
    pub const default_value = Base.default_value;
    pub const equals = Base.equals;
    pub const deinit = Base.deinit;
    pub const hashTreeRoot = Base.hashTreeRoot;
    pub const serializedSize = Base.serializedSize;
    pub const serializeIntoBytes = Base.serializeIntoBytes;
    pub const deserializeFromBytes = Base.deserializeFromBytes;
    pub const serialized = Base.serialized;
};
