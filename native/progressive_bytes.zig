//! Progressive byte lists use hex JSON, while upstream's generic progressive
//! list uses arrays. Delegate only JSON conversion to the ordinary byte list.
const ssz = @import("ssz");
const Base = ssz.FixedProgressiveListType(ssz.UintType(8));
const Json = ssz.ByteListType(512 * 1024 * 1024);

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
    pub const serializeIntoJson = Json.serializeIntoJson;
    pub const deserializeFromJson = Json.deserializeFromJson;
};
